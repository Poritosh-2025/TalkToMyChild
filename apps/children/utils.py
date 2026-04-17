import boto3
import uuid
from botocore.config import Config
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.cache import cache


class S3ClientManager:
    """Singleton manager for S3 client."""

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


def get_child_cache_key(child_id, cache_type="intelligence"):
    """Generate cache key for child data."""
    return f"child_{cache_type}_{child_id}"


def invalidate_child_cache(child_id):
    """Invalidate all cache for a child."""
    cache.delete(get_child_cache_key(child_id, "intelligence"))
    cache.delete(get_child_cache_key(child_id, "achievements"))


def build_prompt_context(child, subjects, traits, interests, dislikes):
    """Build the prompt_context string for AI pipeline."""
    parts = []

    parts.append(f"The child is {child.age} years old and named {child.name}.")

    if subjects:
        subject_list = ", ".join(subjects)
        parts.append(f"He/She is studying {subject_list}.")

    if traits:
        trait_list = ", ".join(traits)
        parts.append(f"His/Her personality is {trait_list}.")

    if interests:
        interest_list = ", ".join(interests)
        parts.append(f"He/She is interested in {interest_list}.")

    if dislikes:
        dislike_list = ", ".join(dislikes)
        parts.append(f"Avoid topics related to {dislike_list}.")

    return " ".join(parts)
