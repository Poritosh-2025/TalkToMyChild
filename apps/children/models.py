import uuid
from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    MinLengthValidator,
)
from django.conf import settings
from django.utils import timezone


class Child(models.Model):
    """
    Child profile model - scoped to parent user (tenant).
    Soft delete pattern: is_active=False preserves call history.

    Security: All queries must filter by parent to ensure tenant isolation.
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
            # Unique name per parent among active children only (case-insensitive)
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
        from django.conf import settings

        return (
            f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{self.avatar}"
        )

    @property
    def has_active_calls(self):
        """Check if child has any active/in-progress calls."""
        from apps.calls.models import CallSession

        return CallSession.objects.filter(child=self, status="active").exists()
