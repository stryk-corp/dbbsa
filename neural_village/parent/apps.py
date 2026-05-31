from django.apps import AppConfig


class ParentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'neural_village.parent'
    verbose_name = 'DBBSA Parent Portal'
