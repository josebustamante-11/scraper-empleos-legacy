import os
from dotenv import load_dotenv

# # Carga .env en local; en GitHub Actions las vars vienen de Secrets
# load_dotenv()


class Settings:
	"""
	Clase estándar para acceder a variables de entorno del proyecto.
	Carga automáticamente el archivo .env si existe.
	Uso:
		settings = Settings()
		db_url = settings.DB_URL
	"""
	def __init__(self):
		load_dotenv()

	@staticmethod
	def _as_bool(value: str | None, default: bool = False) -> bool:
		if value is None:
			return default
		return value.strip().lower() in ("1", "true", "yes", "on")

	@property
	def DB_URL(self):
		return os.environ.get("DB_URL")

	@property
	def DB_URL_POOLER(self):
		return os.environ.get("DB_URL_POOLER")

	@property
	def WP_URL(self):
		return os.environ.get("WP_URL")

	@property
	def WP_USER(self):
		return os.environ.get("WP_USER")

	@property
	def WP_APP_PASSWORD(self):
		return os.environ.get("WP_APP_PASSWORD")
	
	@property
	def SCRAPING_TARGET_URL(self):
		return os.environ.get("SCRAPING_TARGET_URL")

	@property
	def SCRAPING_FETCH_DETAIL_PAGES(self):
		return os.environ.get("SCRAPING_FETCH_DETAIL_PAGES", "true")

	@property
	def SCRAPING_MAX_PAGES(self):
		return int(os.environ.get("SCRAPING_MAX_PAGES", "10"))

	@property
	def SCRAPING_DEBUG_LIMIT(self):
		"""Límite de items a procesar por lote (0 = sin límite). Solo para pruebas."""
		return int(os.environ.get("SCRAPING_DEBUG_LIMIT", "0"))

	@property
	def SCRAPING_BATCH_DELAY(self):
		"""Segundos de espera entre lotes para no saturar el servidor."""
		return float(os.environ.get("SCRAPING_BATCH_DELAY", "1.0"))

	@property
	def TELEGRAM_ENABLED(self):
		return self._as_bool(os.environ.get("TELEGRAM_ENABLED", "false"))

	@property
	def TELEGRAM_BOT_TOKEN(self):
		return os.environ.get("TELEGRAM_BOT_TOKEN")

	@property
	def TELEGRAM_CHAT_ID(self):
		return os.environ.get("TELEGRAM_CHAT_ID")

	@property
	def DB_TABLE(self):
		"""Nombre de la tabla PostgreSQL. Por defecto 'scraped_posts'."""
		return os.environ.get("DB_TABLE", "scraped_posts")

	# Agrega aquí más propiedades según tus variables de entorno

settings = Settings()