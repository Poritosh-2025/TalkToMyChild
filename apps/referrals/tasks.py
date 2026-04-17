from celery import shared_task
from django.utils import timezone
from .services import ReferralService
import logging

logger = logging.getLogger(__name__)


@shared_task
def expire_pending_referrals():
    """
    Celery task to expire pending referrals that are past their expiry date.
    Runs every hour via Celery beat.
    """
    try:
        expired_count = ReferralService.expire_pending_referrals()
        if expired_count > 0:
            logger.info(f"Expired {expired_count} pending referrals.")
        return expired_count
    except Exception as e:
        logger.error(f"Failed to expire referrals: {str(e)}")
        raise


@shared_task
def check_and_expire_referral(referral_id):
    """
    Check and expire a specific referral if it's past its expiry date.
    """
    from .models import Referral

    try:
        referral = Referral.objects.get(id=referral_id)
        if referral.status == "PENDING" and referral.is_expired():
            referral.mark_as_expired()
            from .utils import invalidate_referral_cache

            invalidate_referral_cache(referral.referrer_id)
            return True
    except Referral.DoesNotExist:
        pass
    return False
