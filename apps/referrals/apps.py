from django.apps import AppConfig


class ReferralsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.referrals"
    label = "referrals"
    verbose_name = "Referral System"

    def ready(self):
        # Import signals to ensure they are registered
        import apps.referrals.signals  # noqa
