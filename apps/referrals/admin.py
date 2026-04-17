from django.contrib import admin
from django.utils.html import format_html
from .models import Referral, UserReferralCode


@admin.register(UserReferralCode)
class UserReferralCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "user_email", "created_at"]
    search_fields = ["code", "user__email"]
    readonly_fields = ["id", "created_at"]
    raw_id_fields = ["user"]

    def user_email(self, obj):
        return obj.user.email

    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "referrer_email",
        "referred_email",
        "status",
        "credits_issued",
        "redeemed_at",
        "expires_at",
        "is_expired_badge",
    ]
    list_filter = ["status", "credits_issued", "created_at"]
    search_fields = ["referrer__email", "referred_email"]
    readonly_fields = ["id", "created_at"]
    raw_id_fields = ["referrer", "referred_user"]
    actions = ["mark_as_completed", "mark_as_expired", "force_expire_selected"]

    def referrer_email(self, obj):
        return obj.referrer.email

    referrer_email.short_description = "Referrer"
    referrer_email.admin_order_field = "referrer__email"

    def is_expired_badge(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">✓ Expired</span>')
        return format_html('<span style="color: green;">Active</span>')

    is_expired_badge.short_description = "Expired Status"

    def mark_as_completed(self, request, queryset):
        from django.utils import timezone

        updated = queryset.filter(status="PENDING").update(
            status="COMPLETED", redeemed_at=timezone.now()
        )
        self.message_user(request, f"{updated} referral(s) marked as completed.")

    mark_as_completed.short_description = "Mark selected as completed"

    def mark_as_expired(self, request, queryset):
        updated = queryset.filter(status="PENDING").update(status="EXPIRED")
        self.message_user(request, f"{updated} referral(s) marked as expired.")

    mark_as_expired.short_description = "Mark selected as expired"

    def force_expire_selected(self, request, queryset):
        """Force expire selected referrals regardless of current expiry date."""
        updated = queryset.filter(status="PENDING").update(status="EXPIRED")
        self.message_user(request, f"{updated} referral(s) force-expired.")

    force_expire_selected.short_description = "Force expire selected referrals"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("referrer", "referred_user")
