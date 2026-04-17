import re
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth.password_validation import validate_password


def validate_s3_key(value):
    """
    Validate S3 object key format for security.
    Prevents path traversal and injection attacks.
    """
    if not value:
        return value

    if ".." in value:
        raise ValidationError("Invalid S3 key: path traversal not allowed.")

    if "//" in value:
        raise ValidationError("Invalid S3 key: double slashes not allowed.")

    pattern = r"^[a-zA-Z0-9/_.-]+$"
    if not re.match(pattern, value):
        raise ValidationError(
            "Invalid S3 key format. Use only letters, numbers, /, _, -, and ."
        )

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


def validate_child_password(value):
    """
    Validate child password using Django's password validators.
    """
    validate_password(value)


def validate_attribute_name(value):
    """
    Validate attribute names (subjects, traits, interests, dislikes).
    """
    if not value or not value.strip():
        raise ValidationError("Attribute name cannot be empty.")

    if len(value) > 100:
        raise ValidationError("Attribute name must be less than 100 characters.")

    return value.strip()
