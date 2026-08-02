"""
test_telegram.py — Prueba del canal Telegram integrado en notifier.py

Requisitos en tu .env:
    TELEGRAM_ENABLED=true
    TELEGRAM_BOT_TOKEN=<tu token real>
    TELEGRAM_CHAT_ID=<tu chat id real>

Uso:
    python test_telegram.py
"""

from src.config import settings
from src.services.notifier import bus, Event


def main():
    print("Config actual:")
    print(f"  TELEGRAM_ENABLED  = {settings.TELEGRAM_ENABLED}")
    print(f"  TELEGRAM_BOT_TOKEN = {'(seteado)' if settings.TELEGRAM_BOT_TOKEN else '(vacío)'}")
    print(f"  TELEGRAM_CHAT_ID  = {settings.TELEGRAM_CHAT_ID}")
    print()

    if not settings.TELEGRAM_ENABLED:
        print("⚠️  TELEGRAM_ENABLED está en 'false' en tu .env.")
        print("    Cambialo a 'true' y volvé a correr este script.")
        return

    print("Enviando notificación de prueba (evento SUMMARY)...")
    bus.emit(
        Event.SUMMARY,
        sources_processed=1,
        total_scraped=10,
        inserted=3,
        published_ok=3,
        entities_without_logo=0,
        elapsed="1.2s",
    )
    print("✅ Listo. Revisá tu chat de Telegram para confirmar que llegó el mensaje.")
    print("   Si no llegó nada, revisá los logs de arriba (warnings de loguru) para ver el error real.")


if __name__ == "__main__":
    main()