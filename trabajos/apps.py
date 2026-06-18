from django.apps import AppConfig


class TrabajosConfig(AppConfig):
    name = "trabajos"

    def ready(self):
        import trabajos.signals  # noqa: F401
