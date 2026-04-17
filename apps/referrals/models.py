import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class UserReferralCode(models.Model):
    """
    Stores the unique referral code for each user.
    One-to-one with User for fast lookup.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referral_code_obj",
    )
    code = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        help_text="Unique alphanumeric referral code (uppercase)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["code"], name="idx_referral_code"),
        ]

    def __str__(self):
        return f"{self.user.email}: {self.code}"


class Referral(models.Model):
    """
    Tracks each referral invitation sent by a user.
    Status flow: PENDING -> COMPLETED or EXPIRED

    All emails are normalized to lowercase for case-insensitive lookups.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("EXPIRED", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="referrals_sent",
    )
    referred_email = models.EmailField(max_length=254)
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referred_by",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="PENDING", db_index=True
    )
    credits_issued = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    redeemed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["referrer", "status"], name="idx_referrer_status"),
            models.Index(fields=["expires_at"], name="idx_expires_at"),
            models.Index(fields=["referred_email"], name="idx_referred_email"),
        ]
        constraints = [
            # Prevent duplicate pending referrals to same email from same referrer
            models.UniqueConstraint(
                fields=["referrer", "referred_email"],
                condition=models.Q(status="PENDING"),
                name="unique_pending_referral_per_email",
            ),
            # Prevent multiple completed referrals to same email
            models.UniqueConstraint(
                fields=["referrer", "referred_email"],
                condition=models.Q(status="COMPLETED"),
                name="unique_completed_referral_per_email",
            ),
        ]

    def __str__(self):
        return f"{self.referrer.email} -> {self.referred_email} ({self.status})"

    def save(self, *args, **kwargs):
        """Normalize email to lowercase before saving."""
        if self.referred_email:
            self.referred_email = self.referred_email.lower()
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if referral has expired."""
        return timezone.now() > self.expires_at

    def can_be_redeemed(self):
        """Check if referral is eligible for redemption."""
        return self.status == "PENDING" and not self.is_expired()

    def mark_as_completed(self, referred_user):
        """Mark referral as completed with the referred user."""
        self.referred_user = referred_user
        self.status = "COMPLETED"
        self.redeemed_at = timezone.now()
        self.save(update_fields=["referred_user", "status", "redeemed_at"])

    def mark_as_expired(self):
        """Mark referral as expired."""
        if self.status == "PENDING":
            self.status = "EXPIRED"
            self.save(update_fields=["status"])
