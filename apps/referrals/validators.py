import re
from django.core.exceptions import ValidationError
from django.conf import settings


def validate_referral_code(value):
    """
    Validate and normalize referral code format.
    Format: uppercase alphanumeric, exactly REFERRAL_CODE_LENGTH characters.
    """
    if not value:
        return value

    # Convert to uppercase
    value = value.upper()

    expected_length = getattr(settings, "REFERRAL_CODE_LENGTH", 8)

    if len(value) != expected_length:
        raise ValidationError(
            f"Referral code must be exactly {expected_length} characters."
        )

    pattern = r"^[A-Z0-9]+$"
    if not re.match(pattern, value):
        raise ValidationError(
            "Referral code must contain only uppercase letters and numbers."
        )

    return value


def validate_not_self_referral(referrer_email, referred_email):
    """Validate that a user cannot refer themselves."""
    if referrer_email.lower() == referred_email.lower():
        raise ValidationError("You cannot use your own referral code.")


def validate_email_not_registered(email):
    """Check if email is already registered."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError("This email is already registered on TalkToMyChild.")
