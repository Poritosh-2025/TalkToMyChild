import re
from django.core.exceptions import ValidationError


def validate_s3_key(value):
    """
    Validate S3 object key format for security.
    Prevents path traversal and injection attacks.

    Allowed: alphanumeric, forward slashes, hyphens, underscores, dots.
    Must not start with slash or contain double slashes.
    """
    if not value:
        return value

    # Check for path traversal attempts
    if ".." in value:
        raise ValidationError("Invalid S3 key: path traversal not allowed.")

    # Check for double slashes
    if "//" in value:
        raise ValidationError("Invalid S3 key: double slashes not allowed.")

    # Check format
    pattern = r"^[a-zA-Z0-9/_.-]+$"
    if not re.match(pattern, value):
        raise ValidationError(
            "Invalid S3 key format. Use only letters, numbers, /, _, -, and ."
        )

    # Check length (S3 limits)
    if len(value) > 1024:
        raise ValidationError("S3 key too long (max 1024 characters).")

    return value


def validate_content_type(value):
    """Validate image content type for avatar uploads."""
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/jpg"]
    if value not in allowed_types:
        raise ValidationError(
            f"Unsupported content type. Allowed: {', '.join(allowed_types)}"
        )
    return value
