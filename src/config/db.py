"""
db.py — Conexión y operaciones con PostgreSQL (Supabase)

Cómo obtener el DB_URL de Supabase:
    1. supabase.com → Tu proyecto → Settings → Database
    2. Connection string → URI → copiá el string completo
    3. Reemplazá [YOUR-PASSWORD] con tu contraseña real
    4. Pegalo en el .env como DB_URL=postgresql://...

El script crea la tabla automáticamente en el primer run.
No necesitás hacer nada manualmente en Supabase.
"""

import os
import psycopg2

from psycopg2.extras import RealDictCursor
from psycopg2 import OperationalError
from psycopg2 import sql
from loguru import logger
from src.config import settings


# TABLA = 'scraped_posts_local'
TABLA = settings.DB_TABLE


def _table_identifier():
    return sql.Identifier(TABLA)


def get_connection():
    """Retorna una conexión a PostgreSQL."""
    db_url = settings.DB_URL_POOLER
    if not db_url:
        raise ValueError(
            "DB_URL_POOLER no está configurado. "
            "Definilo en el .env o en los GitHub Secrets."
        )
    return psycopg2.connect(db_url, connect_timeout=8)


def init_db() -> bool:
    """
    Crea la tabla 'scraped_posts' si no existe.
    Se llama automáticamente al inicio de cada run.
    """
    create_table_sql = sql.SQL("""
    CREATE TABLE IF NOT EXISTS {} (
        id              SERIAL PRIMARY KEY,
        slug            VARCHAR(500) UNIQUE NOT NULL,
        url             TEXT,
        wp_post_id      INTEGER DEFAULT NULL,
        wp_published_at TIMESTAMP DEFAULT NULL,
        wp_need_update  BOOLEAN NOT NULL DEFAULT FALSE,
        created_at      TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """).format(_table_identifier())
    create_index_sql = sql.SQL(
        "CREATE INDEX IF NOT EXISTS {} ON {}(slug);"
    ).format(
        sql.Identifier(f"idx_{TABLA}_slug"),
        _table_identifier(),
    )
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_table_sql)
                cur.execute(create_index_sql)
            conn.commit()
        logger.info("DB inicializada correctamente")
        return True
    except OperationalError as e:
        error_text = " ".join(str(e).split())
        logger.error(f"Error inicializando DB: {error_text}")
        lowered = error_text.lower()
        if "could not translate host name" in lowered:
            logger.error("Tip: no se pudo resolver el host de DB. Revisa DNS/red o DB_URL.")
        return False
    except Exception as e:
        logger.error(f"Error inicializando DB: {e}")
        return False


def count_new_slugs(slugs: list[str]) -> int:
    """
    Consulta liviana: cuenta cuántos slugs NO existen aún en la DB.
    No inserta nada — sirve para decidir si vale la pena paginar más.
    """
    if not slugs:
        return 0
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql.SQL("""
            SELECT COUNT(*) FROM UNNEST(%s::text[]) AS s(slug)
            WHERE NOT EXISTS (
                SELECT 1 FROM {} p
                WHERE p.slug = s.slug 
                and p.wp_post_id IS NOT NULL
            )
        """).format(_table_identifier()), (slugs,))
        return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Error en count_new_slugs: {e}")
        return len(slugs)  # ante la duda, asumir que todos son nuevos
    finally:
        cur.close()
        conn.close()


def sync_posts(scraped_items: list[dict], return_stats: bool = False):
    conn = get_connection()
    cur = conn.cursor()

    try:
        scraped_slugs = [item["slug"] for item in scraped_items]
        scraped_urls  = [item["url"]  for item in scraped_items]

        # Fase 1: insertar solo los nuevos — Postgres hace la comparación
        cur.execute(sql.SQL("""
            INSERT INTO {} (slug, url)
            SELECT s.slug, s.url
            FROM UNNEST(%s::text[], %s::text[]) AS s(slug, url)
            WHERE NOT EXISTS (
                SELECT 1 FROM {} p WHERE p.slug = s.slug
            )
        """).format(_table_identifier(), _table_identifier()), (scraped_slugs, scraped_urls))

        inserted = cur.rowcount  # cuántos se insertaron
        conn.commit()

        # Fase 2: pendientes sin wp_post_id
        cur.execute(
            sql.SQL("SELECT id, slug, url FROM {} WHERE wp_post_id IS NULL").format(
                _table_identifier()
            )
        )
        pending = [{"id": r[0], "slug": r[1], "url": r[2]} for r in cur.fetchall()]

        logger.info(f"✅ Nuevos insertados: {inserted}")
        logger.info(f"⏭️  Ya existían: {len(scraped_items) - inserted}")
        logger.info(f"📋 Pendientes WordPress: {len(pending)}")

        if return_stats:
            return pending, inserted
        return pending

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error: {e}")
        if return_stats:
            return [], 0
        return []

    finally:
        cur.close()
        conn.close()


def sync_posts_pendientes():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT id, slug, url FROM {str(_table_identifier().string)} WHERE wp_post_id IS NULL limit 5"
        )
        pending_db = [
            {"id": r[0], "slug": r[1], "url": r[2]} for r in cur.fetchall()
        ]
        return pending_db
    except Exception as e:
        logger.error(f"Error consultando pendientes en DB: {e}")
        return []
    finally:
        cur.close()
        conn.close()


def update_wp_fields(
    updates: list[dict],
    overwrite: bool = False
) -> int:
    """
    updates: lista de dicts con:
      {
        "id": 123,
        "wp_post_id": 999,                 # int o None
        "wp_published_at": datetime | str | None  # datetime o 'YYYY-MM-DD HH:MM:SS' o ISO
      }

    overwrite:
      - False: solo actualiza si wp_post_id/wp_published_at están NULL en la tabla
      - True: sobreescribe aunque ya existan valores
    """
    if not updates:
        return 0

    conn = get_connection()
    cur = conn.cursor()

    try:
        ids = [u["id"] for u in updates]
        wp_ids = [u.get("wp_post_id") for u in updates]
        wp_dates = [u.get("wp_published_at") for u in updates]

        # Nota: psycopg2 adapta datetime automáticamente. Si te llegan strings ISO, también suele adaptarlos,
        # pero si quieres, puedes convertirlos tú antes.

        if overwrite:
            update_sql = sql.SQL("""
                UPDATE {} p
                SET
                    wp_post_id = u.wp_post_id,
                    wp_published_at = u.wp_published_at
                FROM UNNEST(%s::bigint[], %s::int[], %s::timestamp[]) AS u(id, wp_post_id, wp_published_at)
                WHERE p.id = u.id;
            """).format(_table_identifier())
        else:
            # Solo llena campos si están NULL en la tabla (no pisa lo existente)
            update_sql = sql.SQL("""
                UPDATE {} p
                SET
                    wp_post_id = COALESCE(p.wp_post_id, u.wp_post_id),
                    wp_published_at = COALESCE(p.wp_published_at, u.wp_published_at)
                FROM UNNEST(%s::bigint[], %s::int[], %s::timestamp[]) AS u(id, wp_post_id, wp_published_at)
                WHERE p.id = u.id
                  AND (p.wp_post_id IS NULL OR p.wp_published_at IS NULL);
            """).format(_table_identifier())

        cur.execute(update_sql, (ids, wp_ids, wp_dates))
        updated = cur.rowcount
        conn.commit()

        logger.info(f"✅ Registros actualizados: {updated}")
        return updated

    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error actualizando WP fields: {e}")
        return 0

    finally:
        cur.close()
        conn.close()


