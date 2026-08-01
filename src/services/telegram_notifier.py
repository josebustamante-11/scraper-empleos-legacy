# Este módulo fue reemplazado por src/services/notifier.py
# que implementa un sistema de notificaciones reactivo y escalable.
#
# Para emitir notificaciones usa el bus global:
#
#   from src.services.notifier import bus, Event
#   bus.emit(Event.CRITICAL, stage="mi_etapa", detail="descripción")
#   bus.emit(Event.SUMMARY, inserted=5, published_ok=5, ...)
#
# Para agregar un canal nuevo (email, Slack, etc.) hereda NotificationChannel
# y registra la instancia: bus.register(MiCanal())

