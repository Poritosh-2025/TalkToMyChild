from django.conf import settings
from django.db import transaction
from django.utils import timezone

from datetime import timedelta
from .models import Referral, UserReferralCode
from .selectors import (
    get_referral_code_by_code,
    get_referral_by_code_and_email,
    get_pending_referrals_for_expiry,
    get_referral_code_for_user,
)
from .utils import (
    generate_unique_referral_code,
    invalidate_referral_cache,
    normalize_email,
)
from .validators import validate_not_self_referral


class ReferralService:
    """Business logic for referral management."""

    @staticmethod
    def _add_credits(user, amount, reason, source, source_id):
        """
        Add credits to user with fallback if CreditService not available.
        This allows the referral system to work even if credits app is not yet implemented.
        """
        try:
            # Try to use the CreditService if available
            from apps.credits.services import CreditService

            return CreditService.add_credits(user, amount, reason, source, source_id)
        except (ImportError, ModuleNotFoundError, AttributeError):
            # Fallback: update user's credit_balance directly
            with transaction.atomic():
                user.credit_balance = getattr(user, "credit_balance", 0) + amount
                user.save(update_fields=["credit_balance"])

                # Create credit transaction record if CreditTransaction model exists
                try:
                    from apps.credits.models import CreditTransaction

                    CreditTransaction.objects.create(
                        user=user,
                        amount=amount,
                        transaction_type="REFERRAL_BONUS",
                        reference_id=source_id,
                        description=reason,
                    )
                except (ImportError, ModuleNotFoundError):
                    # CreditTransaction model not available, just log
                    pass

            return amount

    @staticmethod
    @transaction.atomic
    def create_referral_code(user):
        """
        Create a unique referral code for a user.
        Called automatically via signal on user creation.
        """
        # Check if code already exists
        existing = get_referral_code_for_user(user)
        if existing:
            return existing

        code = generate_unique_referral_code()
        referral_code = UserReferralCode.objects.create(user=user, code=code)
        return referral_code

    @staticmethod
    @transaction.atomic
    def create_referral_invitation(referrer, email):
        """
        Create a new referral invitation.
        Used when a user manually invites someone.
        """
        normalized_email = normalize_email(email)

        # Check if email is already registered
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if User.objects.filter(email=normalized_email).exists():
            raise ValueError("This email is already registered on TalkToMyChild.")

        # Check for existing pending referral
        existing = Referral.objects.filter(
            referrer=referrer, referred_email=normalized_email, status="PENDING"
        ).first()

        if existing:
            raise ValueError("A pending invitation already exists for this email.")

        # Check for existing completed referral
        completed = Referral.objects.filter(
            referrer=referrer, referred_email=normalized_email, status="COMPLETED"
        ).exists()

        if completed:
            raise ValueError("This email has already used your referral link.")

        # Create new referral
        referral = Referral.objects.create(
            referrer=referrer,
            referred_email=normalized_email,
            expires_at=timezone.now() + timedelta(days=settings.REFERRAL_EXPIRY_DAYS),
        )

        # Invalidate cache
        invalidate_referral_cache(referrer.id)

        return referral

    @staticmethod
    @transaction.atomic
    def redeem_referral(referral_code, new_user):
        """
        Redeem a referral code for a new user.
        Issues credits to both referrer and referee.
        Returns dict with credit amounts.

        Uses select_for_update() to prevent race conditions.
        """
        # Get referral code object
        code_obj = get_referral_code_by_code(referral_code)
        if not code_obj:
            raise ValueError("Invalid referral code.")

        referrer = code_obj.user
        referee = new_user

        # Prevent self-referral
        if referrer.id == referee.id:
            raise ValueError("You cannot use your own referral code.")

        # Check for existing completed referral for this email
        normalized_email = normalize_email(referee.email)
        existing_referral = Referral.objects.filter(
            referrer=referrer, referred_email=normalized_email, status="COMPLETED"
        ).first()

        if existing_referral:
            raise ValueError("This referral code has already been used by this email.")

        # Get or create referral record with select_for_update to prevent race conditions
        referral, created = Referral.objects.select_for_update().get_or_create(
            referrer=referrer,
            referred_email=normalized_email,
            defaults={
                "expires_at": timezone.now()
                + timedelta(days=settings.REFERRAL_EXPIRY_DAYS)
            },
        )

        # Validate referral can be redeemed
        if not referral.can_be_redeemed():
            if referral.is_expired():
                raise ValueError("This referral link has expired.")
            if referral.status == "COMPLETED":
                raise ValueError("This referral has already been used.")
            raise ValueError("This referral cannot be redeemed.")

        # Issue credits (if not already issued)
        referrer_credits = 0
        referee_credits = 0

        if not referral.credits_issued:
            credit_amount = settings.REFERRAL_CREDIT_AMOUNT

            # Issue credits to referrer
            referrer_credits = ReferralService._add_credits(
                user=referrer,
                amount=credit_amount,
                reason=f"Referral bonus for inviting {referee.email}",
                source="REFERRAL",
                source_id=str(referral.id),
            )

            # Issue credits to referee
            referee_credits = ReferralService._add_credits(
                user=referee,
                amount=credit_amount,
                reason=f"Signup bonus from referral by {referrer.email}",
                source="REFERRAL_SIGNUP",
                source_id=str(referral.id),
            )

            referral.credits_issued = True
            referral.save(update_fields=["credits_issued"])

        # Mark as completed
        referral.mark_as_completed(referee)

        # Invalidate cache for both users
        invalidate_referral_cache(referrer.id)
        invalidate_referral_cache(referee.id)

        return {
            "referrer_credits_added": referrer_credits,
            "referee_credits_added": referee_credits,
            "referrer_name": referrer.full_name,
            "referral_id": referral.id,
        }

    @staticmethod
    @transaction.atomic
    def expire_pending_referrals():
        """
        Bulk expire all pending referrals that have passed their expiry date.
        Called by Celery beat task.
        Processes in chunks to avoid memory issues.
        """
        expired_referrals = get_pending_referrals_for_expiry()
        total_count = expired_referrals.count()

        if total_count == 0:
            return 0

        # Process in chunks of 1000
        chunk_size = 1000
        total_updated = 0
        referral_ids = list(expired_referrals.values_list("id", flat=True))

        for i in range(0, len(referral_ids), chunk_size):
            chunk_ids = referral_ids[i : i + chunk_size]
            updated = Referral.objects.filter(id__in=chunk_ids).update(status="EXPIRED")
            total_updated += updated

            # Invalidate cache for each referrer in this chunk
            referrals_in_chunk = Referral.objects.filter(
                id__in=chunk_ids
            ).select_related("referrer")
            for referral in referrals_in_chunk:
                invalidate_referral_cache(referral.referrer_id)

        return total_updated

    @staticmethod
    def get_referral_link(user):
        """
        Get the referral link and sharing information for a user.
        """
        referral_code_obj = get_referral_code_for_user(user)

        if not referral_code_obj:
            referral_code_obj = ReferralService.create_referral_code(user)

        from .serializers import ReferralCodeResponseSerializer

        return referral_code_obj

    @staticmethod
    def check_referral_eligibility(referral_code, user_email):
        """
        Check if a referral code is valid for a given email.
        Returns dict with eligibility status and message.
        """
        normalized_email = normalize_email(user_email)
        code_obj = get_referral_code_by_code(referral_code)

        if not code_obj:
            return {"eligible": False, "message": "Invalid referral code."}

        referrer = code_obj.user

        # Check self-referral
        if referrer.email.lower() == normalized_email:
            return {
                "eligible": False,
                "message": "You cannot use your own referral code.",
            }

        # Check if already used (completed)
        completed = Referral.objects.filter(
            referrer=referrer, referred_email=normalized_email, status="COMPLETED"
        ).exists()

        if completed:
            return {
                "eligible": False,
                "message": "This referral code has already been used by this email.",
            }

        # Check for pending but not expired
        pending_referral = Referral.objects.filter(
            referrer=referrer,
            referred_email=normalized_email,
            status="PENDING",
            expires_at__gt=timezone.now(),
        ).first()

        # Check for expired referral
        expired = Referral.objects.filter(
            referrer=referrer, referred_email=normalized_email, status="EXPIRED"
        ).exists()

        if expired:
            return {"eligible": False, "message": "This referral link has expired."}

        return {
            "eligible": True,
            "message": "Referral code is valid.",
            "referrer_name": referrer.full_name,
            "has_pending": pending_referral is not None,
            "expires_at": pending_referral.expires_at if pending_referral else None,
        }
