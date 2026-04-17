import random
import string
import time
from django.conf import settings
from django.core.cache import cache


def generate_unique_referral_code():
    """
    Generate a unique uppercase alphanumeric referral code.
    Retries up to 10 times with exponential backoff if collision occurs.
    """
    length = getattr(settings, "REFERRAL_CODE_LENGTH", 8)
    max_attempts = 10

    for attempt in range(max_attempts):
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

        from .selectors import get_referral_code_by_code

        if not get_referral_code_by_code(code):
            return code

        # Add delay after 5 attempts to reduce collision probability
        if attempt >= 5:
            time.sleep(0.1 * (attempt - 4))

    raise RuntimeError(
        "Unable to generate unique referral code after maximum attempts. Please try again later."
    )


def get_referral_cache_key(user_id, cache_type="stats"):
    """Generate cache key for referral data."""
    return f"referral_{cache_type}_{user_id}"


def invalidate_referral_cache(user_id):
    """Invalidate all referral cache for a user."""
    cache_keys = ["stats", "list"]
    for key_type in cache_keys:
        cache.delete(get_referral_cache_key(user_id, key_type))


def build_share_url(referral_code):
    """Build the full referral signup URL."""
    from django.conf import settings

    base_url = getattr(settings, "FRONTEND_URL", "https://talktomychild.com")
    return f"{base_url}/signup?ref={referral_code}"


def encode_message_for_share(message):
    """Encode message for URL sharing."""
    return message.replace(" ", "+").replace("\n", "%0A")


def normalize_email(email):
    """Normalize email to lowercase for consistent lookups."""
    return email.lower() if email else email
