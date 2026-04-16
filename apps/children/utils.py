import boto3
import uuid
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


class S3ClientManager:
    """Singleton manager for S3 client to avoid recreating connections."""

    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "standard"},
                ),
            )
        return cls._client


def generate_avatar_key(child_id, content_type):
    """Generate a unique S3 key for child avatar."""
    extension = "jpg"
    if "png" in content_type:
        extension = "png"
    elif "webp" in content_type:
        extension = "webp"

    return f"{settings.CHILD_AVATAR_PREFIX}{child_id}/{uuid.uuid4().hex}.{extension}"


def verify_s3_object_exists(key):
    """Verify that an S3 object exists."""
    try:
        client = S3ClientManager.get_client()
        client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
        return True
    except ClientError:
        return False


def get_s3_object_metadata(key):
    """Get S3 object metadata (size, content-type, etc.)."""
    try:
        client = S3ClientManager.get_client()
        response = client.head_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key)
        return {
            "size": response.get("ContentLength", 0),
            "content_type": response.get("ContentType", ""),
            "last_modified": response.get("LastModified"),
        }
    except ClientError:
        return None


def invalidate_child_cache(child_id):
    """Invalidate all cache keys for a child."""
    cache.delete(f"achievements_{child_id}")
    cache.delete(f"child_detail_{child_id}")


def validate_avatar_key_belongs_to_child(avatar_key, child_id):
    """Validate that the avatar key belongs to the specified child."""
    expected_prefix = f"{settings.CHILD_AVATAR_PREFIX}{child_id}/"
    return avatar_key.startswith(expected_prefix)


def get_weekly_streak(call_dates):
    """
    Calculate weekly streak from list of call dates.
    Returns number of consecutive days with calls in the last 7 days.
    """
    if not call_dates:
        return 0

    from datetime import date, timedelta

    unique_dates = set(call_dates)
    today = date.today()
    streak = 0

    for i in range(7):
        check_date = today - timedelta(days=i)
        if check_date in unique_dates:
            streak += 1
        else:
            break

    return streak
