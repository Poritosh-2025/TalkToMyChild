from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class RegisterThrottle(AnonRateThrottle):
    rate = "5/hour"


class LoginThrottle(AnonRateThrottle):
    rate = "10/hour"


class OTPResendThrottle(AnonRateThrottle):
    rate = "3/hour"


class OTPVerifyThrottle(AnonRateThrottle):  # public endpoint, so AnonRateThrottle
    rate = "10/hour"


class PasswordResetRequestThrottle(AnonRateThrottle):
    rate = "3/hour"
