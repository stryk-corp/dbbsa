from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'neural_village.core'
    verbose_name = 'DBBSA Core'

    def ready(self):
        import neural_village.core.signals  # noqa: F401
