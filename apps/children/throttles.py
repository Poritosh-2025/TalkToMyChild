from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class ChildCreateThrottle(UserRateThrottle):
    rate = "10/hour"
    scope = "child_create"


class ChildUpdateThrottle(UserRateThrottle):
    rate = "30/hour"
    scope = "child_update"


class AvatarUploadThrottle(UserRateThrottle):
    rate = "20/hour"
    scope = "avatar_upload"


class AttributeUpdateThrottle(UserRateThrottle):
    rate = "50/hour"
    scope = "attribute_update"


class ChildLoginThrottle(AnonRateThrottle):
    rate = "10/hour"
    scope = "child_login"
