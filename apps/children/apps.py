from django.apps import AppConfig


class ChildrenConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.children"
    label = "children"
    verbose_name = "Child Profiles v2.0"

    def ready(self):
        # Import signals to ensure they are registered
        import apps.children.signals  # noqa
