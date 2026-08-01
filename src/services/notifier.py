"""
notifier.py — Sistema de notificaciones reactivo y escalable.

Diseño basado en un bus de eventos con canales intercambiables:

    bus.emit(Event.SUMMARY, inserted=5, published=5, errors=0)

Los canales se registran una sola vez y reciben únicamente los eventos
que declaran manejar. Para agregar un nuevo canal (email, Slack, etc.):

    1. Crear una clase que herede de NotificationChannel
    2. Implementar handles(event) → bool  y  send(notif) → bool
    3. Registrar: bus.register(MiCanal())

El canal Telegram se registra automáticamente si TELEGRAM_ENABLED=true en .env.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from html import escape
from typing import Any

import httpx
from loguru import logger

from src.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# 1. EVENTOS
# ─────────────────────────────────────────────────────────────────────────────


class Event(str, Enum):
    """Ciclo de vida del scraper. Cada evento lleva un payload de contexto."""

    CRITICAL       = "critical"       # Fallo que corta el flujo completo
    CANARY_FAILED  = "canary_failed"  # El item canary no superó la prueba
    NO_NEW_ITEMS   = "no_new_items"   # Fuente revisada sin registros nuevos
    SUMMARY        = "summary"        # Resumen final de la ejecución


# ─────────────────────────────────────────────────────────────────────────────
# 2. NOTIFICACIÓN
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Notification:
    """Envoltorio que viaja por el bus a todos los canales registrados."""

    event: Event
    payload: dict[str, Any] = field(default_factory=dict)
    source_id: str | None = None
    source_name: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# 3. CANAL BASE
# ─────────────────────────────────────────────────────────────────────────────


class NotificationChannel(ABC):
    """
    Interfaz base para canales de notificación.

    Para agregar un nuevo canal:
        1. Heredar de NotificationChannel
        2. Implementar handles() → qué eventos procesa este canal
        3. Implementar send()    → cómo entrega el mensaje
        4. Registrar en el bus:  bus.register(MiCanal())
    """

    def handles(self, event: Event) -> bool:
        """Retorna True si este canal debe procesar el evento dado.
        Por defecto acepta todos; sobreescribir para filtrar."""
        return True

    @abstractmethod
    def send(self, notif: Notification) -> bool:
        """Envía la notificación. Retorna True si tuvo éxito."""


# ─────────────────────────────────────────────────────────────────────────────
# 4. BUS DE NOTIFICACIONES
# ─────────────────────────────────────────────────────────────────────────────


class NotificationBus:
    """
    Bus central de eventos. Despacha cada Notification a los canales
    que declaran manejar ese tipo de evento.

    Uso:
        bus.emit(Event.CRITICAL, stage="init_db", detail="No se pudo conectar")
        bus.emit(Event.SUMMARY, inserted=3, published_ok=3, ...)
    """

    def __init__(self) -> None:
        self._channels: list[NotificationChannel] = []

    def register(self, channel: NotificationChannel) -> None:
        """Registra un canal. Se pueden registrar múltiples canales."""
        self._channels.append(channel)
        logger.debug(f"Canal de notificación registrado: {type(channel).__name__}")

    def emit(
        self,
        event: Event,
        *,
        source_id: str | None = None,
        source_name: str | None = None,
        **payload: Any,
    ) -> None:
        """
        Emite un evento a todos los canales que lo manejan.
        Los errores de un canal no interrumpen los demás.
        """
        notif = Notification(
            event=event,
            payload=payload,
            source_id=source_id,
            source_name=source_name,
        )
        for channel in self._channels:
            if channel.handles(event):
                try:
                    channel.send(notif)
                except Exception as exc:
                    logger.warning(
                        f"[{type(channel).__name__}] falló al enviar "
                        f"evento '{event.value}': {exc}"
                    )


# Instancia global — se importa desde cualquier módulo con:
#   from src.services.notifier import bus, Event
bus = NotificationBus()


# ─────────────────────────────────────────────────────────────────────────────
# 5. FORMATO DE MENSAJES
# ─────────────────────────────────────────────────────────────────────────────

_DIV = "─" * 20


def _build_message(
    title: str,
    stats: list[str],
    messages: list[str] | None = None,
    elapsed: str | None = None,
) -> str:
    """
    Estructura unificada de todos los mensajes:

        Título
        ─────────────────────
        … stats …
        ─────────────────────   ← si hay duración o mensajes
        ⏱ Duración: X
        ─────────────────────   ← solo si hay mensajes además del footer
        💬 Mensaje 1
        💬 Mensaje 2
    """
    lines = [title, f"<code>{_DIV}</code>"]
    lines.extend(stats)

    footer: list[str] = []
    if elapsed:
        footer.append(f"⏱ Duración   <code>{escape(str(elapsed))}</code>")

    if footer or messages:
        lines.append(f"<code>{_DIV}</code>")
        lines.extend(footer)

    # Sección de mensajes — segundo separador solo si hay footer que separar
    if messages:
        if footer:
            lines.append(f"<code>{_DIV}</code>")
        for msg in messages:
            lines.append(f"💬 {msg}")

    return "\n".join(lines)


def _format_message(notif: Notification) -> str:
    """Genera un mensaje HTML para Telegram con estructura unificada para todos los eventos."""
    p = notif.payload

    _TITLES = {
        Event.CRITICAL:      "🚨 <b>Fallo crítico</b>",
        Event.CANARY_FAILED: "⚠️ <b>Canary fallido — lote abortado</b>",
        Event.NO_NEW_ITEMS:  "ℹ️ <b>Sin novedades</b>",
        Event.SUMMARY:       "📊 <b>Resumen de ejecución</b>",
    }
    title = _TITLES.get(notif.event, f"<b>[{escape(notif.event.value)}]</b>")

    # Fuente (opcional — presente en eventos de fuente individual)
    src_name = notif.source_name or notif.source_id
    stats: list[str] = []
    if src_name:
        src_fmt = (
            f"<b>{escape(src_name)}</b>"
            if notif.source_name
            else f"<code>{escape(src_name)}</code>"
        )
        stats.append(f"🏢 Fuente         {src_fmt}")

    # Estadísticas comunes (acumuladas hasta el momento del evento)
    sources   = p.get("sources_processed", 0)
    scraped   = p.get("total_scraped",     0)
    inserted  = p.get("inserted",          0)
    published = p.get("published_ok",      0)
    elapsed   = p.get("elapsed")

    if sources > 1:
        stats.append(f"🗂 Fuentes        <code>{sources}</code>")
    stats += [
        f"🌐 Scrapeadas    <code>{scraped}</code>",
        f"🆕 En base datos <code>{inserted}</code>",
        f"✅ Publicadas    <code>{published}</code>",
    ]

    # Entidades sin logo — siempre presente en SUMMARY
    if notif.event == Event.SUMMARY:
        ewl = p.get("entities_without_logo", -1)
        if ewl < 0:
            stats.append("🖼 Sin logo       <code>—</code>")
        else:
            label = f"<code>{ewl}</code>" if ewl == 0 else f"<b>{ewl}</b>"
            stats.append(f"🖼 Sin logo       {label}")

    # Sección de mensajes — detalles específicos del evento
    msgs: list[str] = []

    if notif.event == Event.CRITICAL:
        stage  = escape(str(p.get("stage",  "desconocida")))
        detail = escape(str(p.get("detail", "Sin detalle")))
        msgs.append(f"📍 Etapa: <code>{stage}</code>")
        msgs.append(f"❌ {detail}")

    elif notif.event == Event.CANARY_FAILED:
        item   = escape(str(p.get("item_title", "?")))
        reason = escape(str(p.get("reason",     "Sin detalle")))
        msgs.append(f"📄 Item: <code>{item}</code>")
        msgs.append(f"⚠️ {reason}")

    elif notif.event == Event.NO_NEW_ITEMS:
        reviewed = p.get("reviewed", 0)
        if reviewed:
            msgs.append(f"👁 Revisados: <code>{reviewed}</code>")
        msgs.append("No se detectaron registros nuevos.")

    elif notif.event == Event.SUMMARY:
        errors = p.get("publish_errors", 0)
        failed = p.get("mapped_failed",  0)
        source_notes = p.get("source_notes", [])
        if errors:
            msgs.append(f"❌ {errors} error(es) al publicar")
        if failed:
            msgs.append(f"⚠️ {failed} fallido(s) en mapeo")
        for note in source_notes:
            msgs.append(escape(note))
        if not msgs:
            msgs.append("Ejecución completada sin errores.")

    return _build_message(
        title=title,
        stats=stats,
        messages=msgs or None,
        elapsed=elapsed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 6. CANAL TELEGRAM
# ─────────────────────────────────────────────────────────────────────────────


_TELEGRAM_API = "https://api.telegram.org"

# Eventos que el canal Telegram reporta por defecto
_TELEGRAM_DEFAULT_EVENTS = {
    Event.CRITICAL,
    Event.SUMMARY,
}


class TelegramChannel(NotificationChannel):
    """
    Canal de notificaciones vía Telegram Bot API.

    Configuración en .env:
        TELEGRAM_ENABLED=true
        TELEGRAM_BOT_TOKEN=<token del bot>
        TELEGRAM_CHAT_ID=<id del chat o canal>

    Para cambiar qué eventos reporta, pasar un set de Event al constructor:
        bus.register(TelegramChannel(events={Event.CRITICAL}))
    """

    def __init__(self, events: set[Event] | None = None) -> None:
        self._events = events if events is not None else _TELEGRAM_DEFAULT_EVENTS

    def handles(self, event: Event) -> bool:
        return event in self._events

    def _is_configured(self) -> bool:
        if not settings.TELEGRAM_ENABLED:
            return False
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            logger.warning(
                "Telegram habilitado pero faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en el .env"
            )
            return False
        return True

    def send(self, notif: Notification) -> bool:
        if not self._is_configured():
            return False

        endpoint = f"{_TELEGRAM_API}/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

        try:
            message = _format_message(notif)
            payload = {
                "chat_id":                  settings.TELEGRAM_CHAT_ID,
                "text":                     message,
                "parse_mode":               "HTML",
                "disable_web_page_preview": True,
            }
            resp = httpx.post(endpoint, json=payload, timeout=15)
            if not resp.is_success:
                logger.warning(
                    f"Telegram rechazó el mensaje [{resp.status_code}]: {resp.text[:300]}"
                )
                return False
            body = resp.json()
            if not body.get("ok", False):
                logger.warning(f"Telegram respondió ok=false: {body}")
                return False
            return True
        except Exception as exc:
            logger.warning(f"No se pudo enviar notificación a Telegram: {exc}")
            return False


# ─── Registro automático ──────────────────────────────────────
# El canal Telegram se activa solo si TELEGRAM_ENABLED=true en el .env.
# Agregar otros canales aquí o desde main.py con bus.register(MiCanal()).
if settings.TELEGRAM_ENABLED:
    bus.register(TelegramChannel())
