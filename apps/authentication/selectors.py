from django.utils import timezone
from .models import User, OTP, RefreshTokenBlacklist


def get_user_by_email(email):
    try:
        return User.objects.get(email=email)
    except User.DoesNotExist:
        return None


def get_user_by_id(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def get_valid_otp(user, otp_code, otp_type):
    return OTP.objects.filter(
        user=user,
        code=otp_code,
        otp_type=otp_type,
        is_used=False,
        expires_at__gt=timezone.now(),
    ).first()


def is_refresh_token_blacklisted(token):
    return RefreshTokenBlacklist.objects.filter(token=token).exists()
