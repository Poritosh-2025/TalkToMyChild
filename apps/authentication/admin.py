from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTP, RefreshTokenBlacklist


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    list_display = (
        "email",
        "full_name",
        "role",
        "is_email_verified",
        "credit_balance",
        "date_joined",
    )
    list_filter = ("role", "is_email_verified", "auth_provider")

    search_fields = ("email", "full_name")
    ordering = ("-date_joined",)

    readonly_fields = ("id", "date_joined", "last_login")

    fieldsets = (
        ("Basic Info", {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("full_name", "profile_photo")}),
        (
            "Permissions & Roles",
            {"fields": ("role", "is_email_verified")},
        ),
        (
            "Other Info",
            {"fields": ("auth_provider", "credit_balance", "referral_code")},
        ),
        ("Timestamps", {"fields": ("date_joined", "last_login")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password1", "password2"),
            },
        ),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "code",
        "otp_type",
        "is_used",
        "failed_attempts",
        "expires_at",
    )
    list_filter = ("otp_type", "is_used")
    search_fields = ("user__email", "code")
    ordering = ("-created_at",)

    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False  # OTP should not be manually created from admin


@admin.register(RefreshTokenBlacklist)
class RefreshTokenBlacklistAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "expires_at", "blacklisted_at")
    search_fields = ("user__email", "token")
    ordering = ("-blacklisted_at",)

    readonly_fields = ("blacklisted_at",)
