from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class ReferralCreateThrottle(UserRateThrottle):
    """Limit referral creation to 20 per hour per user."""

    rate = "20/hour"
    scope = "referral_create"


class ReferralRedeemThrottle(AnonRateThrottle):
    """Limit referral redemption attempts to 10 per hour per IP."""

    rate = "10/hour"
    scope = "referral_redeem"


class ReferralListThrottle(UserRateThrottle):
    """Limit referral listing to 60 per hour per user."""

    rate = "60/hour"
    scope = "referral_list"


class ReferralCheckThrottle(AnonRateThrottle):
    """Stricter limit for referral check endpoint to prevent abuse."""

    rate = "5/minute"
    scope = "referral_check"
