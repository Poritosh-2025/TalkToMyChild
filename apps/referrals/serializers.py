from rest_framework import serializers
from .models import Referral, UserReferralCode
from .validators import validate_referral_code


class ReferralCodeResponseSerializer(serializers.ModelSerializer):
    """Serializer for returning user's referral code and share links."""

    referral_url = serializers.SerializerMethodField()
    credits_per_referral = serializers.SerializerMethodField()
    share_links = serializers.SerializerMethodField()

    class Meta:
        model = UserReferralCode
        fields = ["code", "referral_url", "credits_per_referral", "share_links"]

    def get_referral_url(self, obj):
        """Generate full referral URL with code (supports multi-tenant subdomains)."""
        from django.conf import settings

        base_url = getattr(settings, "FRONTEND_URL", "https://talktomychild.com")

        # Multi-tenant subdomain support
        if (
            hasattr(obj.user, "tenant")
            and obj.user.tenant
            and obj.user.tenant.subdomain
        ):
            base_url = f"https://{obj.user.tenant.subdomain}.talktomychild.com"

        return f"{base_url}/signup?ref={obj.code}"

    def get_credits_per_referral(self, obj):
        from django.conf import settings

        return getattr(settings, "REFERRAL_CREDIT_AMOUNT", 2)

    def get_share_links(self, obj):
        """Generate platform-specific share links."""
        referral_url = self.get_referral_url(obj)
        message = f"Join TalkToMyChild with my code {obj.code}! {referral_url}"
        encoded_message = message.replace(" ", "+").replace("\n", "%0A")

        return {
            "whatsapp": f"https://wa.me/?text={encoded_message}",
            "sms": f"sms:?body={encoded_message}",
            "copy": referral_url,
            "imessage": f"imessage:?body={encoded_message}",
        }


class ReferralListSerializer(serializers.ModelSerializer):
    """Serializer for listing referrals sent by user."""

    referred_email = serializers.EmailField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    days_until_expiry = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = [
            "id",
            "referred_email",
            "status",
            "status_display",
            "credits_issued",
            "redeemed_at",
            "expires_at",
            "created_at",
            "days_until_expiry",
        ]
        read_only_fields = fields

    def get_days_until_expiry(self, obj):
        """Calculate days until referral expires."""
        from django.utils import timezone

        if obj.status == "PENDING" and obj.expires_at:
            delta = obj.expires_at - timezone.now()
            return max(0, delta.days)
        return None


class ReferralStatsSerializer(serializers.Serializer):
    """Serializer for referral statistics."""

    total_referrals = serializers.IntegerField()
    completed = serializers.IntegerField()
    pending = serializers.IntegerField()
    expired = serializers.IntegerField()
    total_credits_earned = serializers.IntegerField()
    conversion_rate = serializers.SerializerMethodField()

    def get_conversion_rate(self, obj):
        """Calculate conversion rate (completed / total)."""
        total = obj.get("total_referrals", 0)
        completed = obj.get("completed", 0)
        if total > 0:
            return round((completed / total) * 100, 1)
        return 0.0


class ReferralRedeemRequestSerializer(serializers.Serializer):
    """Request serializer for redeeming a referral (internal API)."""

    referral_code = serializers.CharField(
        max_length=12, validators=[validate_referral_code]
    )
    new_user_id = serializers.UUIDField()

    def validate_referral_code(self, value):
        """Convert to uppercase."""
        return value.upper()


class ReferralRedeemResponseSerializer(serializers.Serializer):
    """Response serializer for referral redemption."""

    referrer_credits_added = serializers.IntegerField()
    referee_credits_added = serializers.IntegerField()
    referrer_name = serializers.CharField()
    referral_id = serializers.UUIDField()


class ReferralCreateRequestSerializer(serializers.Serializer):
    """Request serializer for creating a referral (when sending invitation)."""

    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate email format and prevent self-referral."""
        value = value.lower()
        user = self.context.get("user")

        if user and user.email.lower() == value:
            raise serializers.ValidationError(
                "You cannot send a referral to your own email."
            )

        # Check if email already registered
        from django.contrib.auth import get_user_model

        User = get_user_model()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "This email is already registered on TalkToMyChild."
            )

        return value


class ReferralCheckEligibilityResponseSerializer(serializers.Serializer):
    """Response serializer for referral eligibility check."""

    eligible = serializers.BooleanField()
    message = serializers.CharField()
    referrer_name = serializers.CharField(required=False)
    has_pending = serializers.BooleanField(required=False)
    expires_at = serializers.DateTimeField(required=False)
