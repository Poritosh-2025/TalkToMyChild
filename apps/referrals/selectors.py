from django.db.models import Count, Sum, Q, Case, When, Value, IntegerField, F
from django.core.cache import cache
from django.utils import timezone
from .models import Referral, UserReferralCode
from .utils import get_referral_cache_key, normalize_email


def get_referral_code_by_code(code):
    """Get UserReferralCode by code value (case-insensitive)."""
    try:
        return UserReferralCode.objects.select_related("user").get(code=code.upper())
    except UserReferralCode.DoesNotExist:
        return None


def get_referral_code_for_user(user):
    """Get the referral code object for a user."""
    try:
        return UserReferralCode.objects.get(user=user)
    except UserReferralCode.DoesNotExist:
        return None


def get_referral_by_code_and_email(referral_code, email):
    """
    Get a pending referral by code and referred email.
    Used during redemption flow.
    """
    code_obj = get_referral_code_by_code(referral_code)
    if not code_obj:
        return None

    normalized_email = normalize_email(email)

    try:
        return Referral.objects.get(
            referrer=code_obj.user,
            referred_email=normalized_email,
            status="PENDING",
            expires_at__gt=timezone.now(),
        )
    except Referral.DoesNotExist:
        return None


def get_referrals_for_user(user, status=None):
    """
    Get all referrals sent by a user.
    Optionally filter by status.
    """
    queryset = Referral.objects.filter(referrer=user).select_related("referred_user")

    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at")


def get_referral_stats_for_user(user):
    """
    Get aggregated referral statistics for a user.
    Uses caching with fallback if cache is down.
    """
    cache_key = get_referral_cache_key(user.id, "stats")

    # Try cache with error handling
    try:
        cached_stats = cache.get(cache_key)
        if cached_stats is not None:
            return cached_stats
    except Exception:
        # Cache is down, continue to database query
        pass

    # Single query with aggregations
    stats = Referral.objects.filter(referrer=user).aggregate(
        total_referrals=Count("id"),
        completed=Count("id", filter=Q(status="COMPLETED")),
        pending=Count("id", filter=Q(status="PENDING")),
        expired=Count("id", filter=Q(status="EXPIRED")),
        total_credits_earned=Sum(
            Case(
                When(credits_issued=True, then=Value(2)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ),
    )

    # Handle None values
    for key in stats:
        if stats[key] is None:
            stats[key] = 0

    # Try to cache, but don't fail if cache is down
    try:
        cache.set(cache_key, stats, 900)  # 15 minutes
    except Exception:
        pass

    return stats


def get_pending_referrals_for_expiry():
    """Get all pending referrals that have expired."""
    return Referral.objects.filter(status="PENDING", expires_at__lt=timezone.now())


def get_referral_by_id(referral_id, user):
    """Get a specific referral by ID, ensuring it belongs to the user."""
    try:
        return Referral.objects.get(id=referral_id, referrer=user)
    except Referral.DoesNotExist:
        return None


def has_existing_referral(referrer_email, referred_email):
    """Check if a referral already exists between these emails."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    normalized_referrer = normalize_email(referrer_email)
    normalized_referred = normalize_email(referred_email)

    try:
        referrer = User.objects.get(email=normalized_referrer)
        return Referral.objects.filter(
            referrer=referrer,
            referred_email=normalized_referred,
            status__in=["PENDING", "COMPLETED"],
        ).exists()
    except User.DoesNotExist:
        return False
