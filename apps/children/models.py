import uuid
from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
)
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings


class Child(models.Model):
    """
    Child profile model - scoped to parent user (tenant).
    Soft delete pattern: is_active=False preserves call history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="children",
        db_index=True,
    )
    name = models.CharField(
        max_length=100,
        validators=[MinLengthValidator(2)],
        help_text="Child's display name (2-100 characters)",
    )
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(17)],
        help_text="Age must be between 1 and 17",
    )
    avatar = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 object key (e.g., 'avatars/uuid-xxxx/image-hash.jpg')",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Soft delete flag - False hides profile but preserves history",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["parent", "is_active"], name="idx_parent_active"),
            models.Index(fields=["created_at"], name="idx_child_created"),
            models.Index(fields=["parent", "name"], name="idx_parent_name"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                condition=models.Q(is_active=True),
                name="unique_active_child_name_per_parent",
            )
        ]

    def __str__(self):
        return f"{self.name} (parent: {self.parent.email})"

    def soft_delete(self):
        """Soft delete this child profile."""
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def restore(self):
        """Restore a soft-deleted child profile."""
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])

    @property
    def avatar_url(self):
        """Generate full S3 URL from avatar key."""
        if not self.avatar:
            return None
        return (
            f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{self.avatar}"
        )

    @property
    def has_active_calls(self):
        """Check if child has any active/in-progress calls."""
        try:
            from apps.calls.models import CallSession

            return CallSession.objects.filter(child=self, status="active").exists()
        except ImportError:
            return False  # Calls app not yet installed


class ChildProfile(models.Model):
    """
    Child login credentials - separate from Child model for clean separation.
    One-to-one with Child for authentication.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.OneToOneField(
        Child, on_delete=models.CASCADE, related_name="credentials"
    )
    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=128)  # Hashed password
    is_email_verified = models.BooleanField(default=True)  # Pre-verified by parent
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["email"], name="idx_child_email"),
        ]

    def __str__(self):
        return f"Credentials for {self.child.name} ({self.email})"

    def set_password(self, raw_password):
        """Hash and set the password."""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verify the password."""
        return check_password(raw_password, self.password)


class ChildSubject(models.Model):
    """Subject preferences - unlimited, parent-defined."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["child"], name="idx_subject_child"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["child", "name"], name="unique_subject_per_child"
            )
        ]

    def __str__(self):
        return f"{self.child.name}: {self.name}"


class ChildTrait(models.Model):
    """Personality traits - unlimited, parent-defined."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="traits")
    name = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["child"], name="idx_trait_child"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["child", "name"], name="unique_trait_per_child"
            )
        ]

    def __str__(self):
        return f"{self.child.name}: {self.name}"


class ChildInterest(models.Model):
    """Interests - unlimited, parent-defined."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="interests")
    name = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["child"], name="idx_interest_child"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["child", "name"], name="unique_interest_per_child"
            )
        ]

    def __str__(self):
        return f"{self.child.name}: {self.name}"


class ChildDislike(models.Model):
    """Dislikes - unlimited, parent-defined."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="dislikes")
    name = models.CharField(max_length=100, validators=[MinLengthValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["child"], name="idx_dislike_child"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["child", "name"], name="unique_dislike_per_child"
            )
        ]

    def __str__(self):
        return f"{self.child.name}: {self.name}"
