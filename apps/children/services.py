from django.db import transaction
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from botocore.exceptions import ClientError
from .models import Child
from .selectors import get_active_children_count, get_child_by_id
from .utils import (
    generate_avatar_key,
    verify_s3_object_exists,
    invalidate_child_cache,
    validate_avatar_key_belongs_to_child,
    S3ClientManager,
)
from .validators import validate_content_type


class ChildService:
    """Business logic for child profile management."""

    @staticmethod
    @transaction.atomic
    def create_child(parent, name, age):
        """
        Create a new child profile for the parent.
        Validates max children limit and name uniqueness.

        Raises:
            ValueError: If validation fails
        """
        # Check max children limit (race condition safe with select_for_update)
        active_count = (
            Child.objects.select_for_update()
            .filter(parent=parent, is_active=True)
            .count()
        )

        if active_count >= settings.CHILD_MAX_PER_PARENT:
            raise ValueError(
                f"Maximum {settings.CHILD_MAX_PER_PARENT} child profiles allowed."
            )

        # Check name uniqueness (case-insensitive)
        if Child.objects.filter(
            parent=parent, name__iexact=name.strip(), is_active=True
        ).exists():
            raise ValueError("A child with this name already exists in your account.")

        child = Child.objects.create(parent=parent, name=name.strip(), age=age)

        return child

    @staticmethod
    @transaction.atomic
    def update_child(child, name=None, age=None):
        """
        Update child profile fields.
        Validates name uniqueness and age range.

        Raises:
            ValueError: If validation fails
        """
        if name is not None:
            name = name.strip()

            # Check name uniqueness (exclude current child, case-insensitive)
            if (
                Child.objects.filter(
                    parent=child.parent, name__iexact=name, is_active=True
                )
                .exclude(id=child.id)
                .exists()
            ):
                raise ValueError(
                    "A child with this name already exists in your account."
                )

            child.name = name

        if age is not None:
            if not 1 <= age <= 17:
                raise ValueError("Age must be between 1 and 17.")
            child.age = age

        child.save()

        # Invalidate cache
        invalidate_child_cache(child.id)

        return child

    @staticmethod
    def generate_avatar_presigned_url(child, content_type="image/jpeg"):
        """
        Generate S3 presigned PUT URL for avatar upload.

        Returns dict with:
            - upload_url: Presigned URL for client upload
            - avatar_key: S3 object key
            - expires_in: TTL in seconds

        Raises:
            ValueError: If content_type is invalid
            Exception: If S3 client fails
        """
        # Validate content type
        validate_content_type(content_type)

        # Generate unique S3 key
        avatar_key = generate_avatar_key(child.id, content_type)

        # Get S3 client
        s3_client = S3ClientManager.get_client()

        # Generate presigned URL with size limit (5MB)
        try:
            upload_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": avatar_key,
                    "ContentType": content_type,
                    "CacheControl": "max-age=31536000",
                    "ContentLength": 5 * 1024 * 1024,  # 5MB limit
                },
                ExpiresIn=settings.CHILD_AVATAR_TTL,
            )
        except ClientError as e:
            raise Exception(f"Failed to generate upload URL: {str(e)}")

        return {
            "upload_url": upload_url,
            "avatar_key": avatar_key,
            "expires_in": settings.CHILD_AVATAR_TTL,
        }

    @staticmethod
    @transaction.atomic
    def confirm_avatar(child, avatar_key):
        """
        Confirm avatar upload by verifying S3 object exists and updating child.
        Security: Validates that the avatar_key belongs to this child.

        Raises:
            ValueError: If validation fails or file not found
        """
        # Security: Validate avatar_key belongs to this child
        if not validate_avatar_key_belongs_to_child(avatar_key, child.id):
            raise ValueError("Invalid avatar key for this child.")

        # Verify object exists in S3 and get metadata
        if not verify_s3_object_exists(avatar_key):
            raise ValueError("Avatar file not found in storage. Please upload again.")

        # Optional: Verify file size and dimensions (could add with Pillow)
        from .utils import get_s3_object_metadata

        metadata = get_s3_object_metadata(avatar_key)
        if metadata and metadata.get("size", 0) > 5 * 1024 * 1024:  # 5MB limit
            raise ValueError("Avatar file exceeds 5MB limit.")

        # Update child avatar
        child.avatar = avatar_key
        child.save(update_fields=["avatar", "updated_at"])

        # Clear cache
        invalidate_child_cache(child.id)

        return child

    @staticmethod
    @transaction.atomic
    def delete_child(child):
        """Soft delete a child profile."""
        # Check if child has active calls
        if child.has_active_calls:
            raise ValueError(
                "Cannot delete child with active calls. Please end all calls first."
            )

        child.soft_delete()
        invalidate_child_cache(child.id)
        return True

    @staticmethod
    @transaction.atomic
    def restore_child(child):
        """Restore a soft-deleted child profile."""
        if child.is_active:
            raise ValueError("Child profile is already active.")

        # Check name uniqueness when restoring
        if Child.objects.filter(
            parent=child.parent, name__iexact=child.name, is_active=True
        ).exists():
            raise ValueError("Cannot restore: A child with this name already exists.")

        child.restore()
        invalidate_child_cache(child.id)
        return True

    @staticmethod
    def get_avatar_url(child):
        """Get the full avatar URL."""
        return child.avatar_url

    @staticmethod
    def bulk_create_children(parent, children_data):
        """
        Bulk create multiple children (for onboarding flow).

        Args:
            parent: User instance
            children_data: List of dicts with 'name' and 'age'

        Returns:
            List of created Child instances

        Raises:
            ValueError: If any validation fails
        """
        from django.core.validators import ValidationError

        created_children = []
        errors = []

        for idx, data in enumerate(children_data):
            try:
                child = ChildService.create_child(
                    parent=parent, name=data["name"], age=data["age"]
                )
                created_children.append(child)
            except ValueError as e:
                errors.append(f"Child {idx + 1}: {str(e)}")

        if errors:
            raise ValueError("; ".join(errors))

        return created_children
