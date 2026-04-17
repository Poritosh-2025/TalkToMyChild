from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .services import ReferralService


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_referral_code(sender, instance, created, **kwargs):
    """
    Automatically create a referral code for every new user.
    """
    if created:
        try:
            ReferralService.create_referral_code(instance)
        except Exception as e:
            # Log error but don't fail user creation
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Failed to create referral code for user {instance.email}: {str(e)}"
            )
