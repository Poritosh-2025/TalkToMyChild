from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class ChildCreateThrottle(UserRateThrottle):
    """
    Limit child creation to 10 per hour per parent.
    Prevents abuse of the free tier.
    """

    rate = "10/hour"
    scope = "child_create"


class ChildUpdateThrottle(UserRateThrottle):
    """Limit child updates to 30 per hour per parent."""

    rate = "30/hour"
    scope = "child_update"


class AvatarUploadThrottle(UserRateThrottle):
    """Limit avatar upload requests to 20 per hour per parent."""

    rate = "20/hour"
    scope = "avatar_upload"


class AvatarConfirmThrottle(UserRateThrottle):
    """Limit avatar confirmations to 20 per hour per parent."""

    rate = "20/hour"
    scope = "avatar_confirm"
