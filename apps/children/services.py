from django.db import transaction
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import (
    Child,
    ChildProfile,
    ChildSubject,
    ChildTrait,
    ChildInterest,
    ChildDislike,
)
from .selectors import (
    get_active_children_count,
    get_child_by_id,
    get_child_profile_by_email,
    check_email_unique,
)
from .utils import (
    generate_avatar_key,
    verify_s3_object_exists,
    invalidate_child_cache,
    S3ClientManager,
    build_prompt_context,
)
from .validators import validate_content_type, validate_attribute_name


class ChildService:
    """Business logic for child profile management v2.0."""

    @staticmethod
    def _deduplicate_attributes(values):
        """Deduplicate attribute names case-insensitively, preserve first casing."""
        seen = {}
        result = []
        for v in values:
            normalized = v.lower()
            if normalized not in seen:
                seen[normalized] = v
                result.append(v)
        return result

    @staticmethod
    def _replace_attributes(child, model_class, values, field_name="name"):
        """
        Generic attribute replacement.
        Deletes all existing, bulk creates new ones.
        """
        # Delete existing
        model_class.objects.filter(child=child).delete()

        # Bulk create new
        if values:
            cleaned_values = ChildService._deduplicate_attributes(values)
            objects = [
                model_class(child=child, **{field_name: v}) for v in cleaned_values
            ]
            model_class.objects.bulk_create(objects)

        return len(values)

    @staticmethod
    @transaction.atomic
    def create_child(parent, data):
        """
        Create a full child profile including credentials and all attributes.
        One atomic transaction - any failure rolls back everything.
        """
        # Check max children limit
        active_count = get_active_children_count(parent)
        if active_count >= settings.CHILD_MAX_PER_PARENT:
            raise ValueError(
                f"Maximum {settings.CHILD_MAX_PER_PARENT} child profiles allowed."
            )

        # Check name uniqueness
        if Child.objects.filter(
            parent=parent, name__iexact=data["name"], is_active=True
        ).exists():
            raise ValueError("A child with this name already exists in your account.")

        # Check email uniqueness
        if not check_email_unique(data["email"]):
            raise ValueError(
                "This email address is already in use by another child account."
            )

        # Create Child
        child = Child.objects.create(
            parent=parent, name=data["name"].strip(), age=data["age"]
        )

        # Create ChildProfile (credentials)
        child_profile = ChildProfile.objects.create(
            child=child, email=data["email"].lower()
        )
        child_profile.set_password(data["password"])
        child_profile.save()

        # Create attributes
        if data.get("subjects"):
            ChildService._replace_attributes(child, ChildSubject, data["subjects"])

        if data.get("traits"):
            ChildService._replace_attributes(child, ChildTrait, data["traits"])

        if data.get("interests"):
            ChildService._replace_attributes(child, ChildInterest, data["interests"])

        if data.get("dislikes"):
            ChildService._replace_attributes(child, ChildDislike, data["dislikes"])

        return child

    @staticmethod
    @transaction.atomic
    def update_child(child, name=None, age=None):
        """Update child basic fields."""
        if name is not None:
            name = name.strip()
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
        invalidate_child_cache(child.id)

        return child

    @staticmethod
    @transaction.atomic
    def update_credentials(child, email=None, password=None):
        """Update child login credentials."""
        profile = child.credentials

        if email is not None:
            email = email.lower()
            if email != profile.email:
                if not check_email_unique(email, exclude_child_id=child.id):
                    raise ValueError(
                        "This email address is already in use by another child account."
                    )
                profile.email = email

        if password is not None:
            profile.set_password(password)

        profile.save()
        invalidate_child_cache(child.id)

        return profile

    @staticmethod
    @transaction.atomic
    def update_subjects(child, subjects):
        """Replace entire subjects list."""
        count = ChildService._replace_attributes(child, ChildSubject, subjects)
        invalidate_child_cache(child.id)
        return count

    @staticmethod
    @transaction.atomic
    def update_traits(child, traits):
        """Replace entire traits list."""
        count = ChildService._replace_attributes(child, ChildTrait, traits)
        invalidate_child_cache(child.id)
        return count

    @staticmethod
    @transaction.atomic
    def update_interests(child, interests):
        """Replace entire interests list."""
        count = ChildService._replace_attributes(child, ChildInterest, interests)
        invalidate_child_cache(child.id)
        return count

    @staticmethod
    @transaction.atomic
    def update_dislikes(child, dislikes):
        """Replace entire dislikes list."""
        count = ChildService._replace_attributes(child, ChildDislike, dislikes)
        invalidate_child_cache(child.id)
        return count

    @staticmethod
    def generate_avatar_presigned_url(child, content_type="image/jpeg"):
        """Generate S3 presigned PUT URL for avatar upload."""
        validate_content_type(content_type)
        avatar_key = generate_avatar_key(child.id, content_type)

        s3_client = S3ClientManager.get_client()

        try:
            upload_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                    "Key": avatar_key,
                    "ContentType": content_type,
                    "CacheControl": "max-age=31536000",
                    "ContentLength": 5 * 1024 * 1024,
                },
                ExpiresIn=settings.CHILD_AVATAR_TTL,
            )
        except Exception as e:
            raise Exception(f"Failed to generate upload URL: {str(e)}")

        return {
            "upload_url": upload_url,
            "avatar_key": avatar_key,
            "expires_in": settings.CHILD_AVATAR_TTL,
        }

    @staticmethod
    @transaction.atomic
    def confirm_avatar(child, avatar_key):
        """Confirm avatar upload by verifying S3 object exists."""
        expected_prefix = f"{settings.CHILD_AVATAR_PREFIX}{child.id}/"
        if not avatar_key.startswith(expected_prefix):
            raise ValueError("Invalid avatar key for this child.")

        if not verify_s3_object_exists(avatar_key):
            raise ValueError("Avatar file not found in storage. Please upload again.")

        child.avatar = avatar_key
        child.save(update_fields=["avatar", "updated_at"])
        invalidate_child_cache(child.id)

        return child

    @staticmethod
    @transaction.atomic
    def delete_child(child):
        """Soft delete a child profile."""
        if child.has_active_calls:
            raise ValueError(
                "Cannot delete child with active calls. Please end all calls first."
            )

        child.soft_delete()
        invalidate_child_cache(child.id)
        return True

    @staticmethod
    def authenticate_child(email, password):
        """Authenticate child using email and password."""
        profile = get_child_profile_by_email(email)

        if not profile:
            return None

        child = profile.child

        if not child.is_active:
            return None

        if not profile.check_password(password):
            return None

        # Update last login
        profile.last_login = timezone.now()
        profile.save(update_fields=["last_login"])

        return child
