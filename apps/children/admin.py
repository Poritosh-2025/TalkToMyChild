from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.hashers import make_password
from .models import (
    Child,
    ChildProfile,
    ChildSubject,
    ChildTrait,
    ChildInterest,
    ChildDislike,
)


class ChildProfileInline(admin.StackedInline):
    model = ChildProfile
    can_delete = False
    verbose_name_plural = "Login Credentials"
    fields = ["email", "password", "is_email_verified", "last_login"]
    readonly_fields = ["last_login"]


class ChildSubjectInline(admin.TabularInline):
    model = ChildSubject
    extra = 1
    fields = ["name"]


class ChildTraitInline(admin.TabularInline):
    model = ChildTrait
    extra = 1
    fields = ["name"]


class ChildInterestInline(admin.TabularInline):
    model = ChildInterest
    extra = 1
    fields = ["name"]


class ChildDislikeInline(admin.TabularInline):
    model = ChildDislike
    extra = 1
    fields = ["name"]


@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "age",
        "parent_email",
        "is_active",
        "avatar_preview",
        "created_at",
    ]
    list_filter = ["is_active", "age", "created_at"]
    search_fields = ["name", "parent__email", "parent__full_name"]
    raw_id_fields = ["parent"]
    readonly_fields = ["id", "created_at", "updated_at", "avatar_preview"]
    inlines = [
        ChildProfileInline,
        ChildSubjectInline,
        ChildTraitInline,
        ChildInterestInline,
        ChildDislikeInline,
    ]
    actions = ["soft_delete_selected", "restore_selected"]

    fieldsets = (
        ("Basic Information", {"fields": ("id", "name", "age", "parent", "is_active")}),
        ("Avatar", {"fields": ("avatar", "avatar_preview")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def parent_email(self, obj):
        return obj.parent.email

    parent_email.short_description = "Parent"
    parent_email.admin_order_field = "parent__email"

    def avatar_preview(self, obj):
        if obj.avatar_url:
            return format_html(
                '<img src="{}" width="50" height="50" style="border-radius: 50%;" />',
                obj.avatar_url,
            )
        return "No avatar"

    avatar_preview.short_description = "Avatar"

    def soft_delete_selected(self, request, queryset):
        count = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f"{count} child profile(s) soft-deleted.")

    soft_delete_selected.short_description = "Soft delete selected children"

    def restore_selected(self, request, queryset):
        count = 0
        for child in queryset.filter(is_active=False):
            if not Child.objects.filter(
                parent=child.parent, name__iexact=child.name, is_active=True
            ).exists():
                child.is_active = True
                child.save()
                count += 1
        self.message_user(request, f"{count} child profile(s) restored.")

    restore_selected.short_description = "Restore selected children"


@admin.register(ChildProfile)
class ChildProfileAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "child_name",
        "is_email_verified",
        "last_login",
        "created_at",
    ]
    list_filter = ["is_email_verified", "created_at"]
    search_fields = ["email", "child__name"]
    raw_id_fields = ["child"]
    readonly_fields = ["last_login", "created_at", "updated_at"]

    def child_name(self, obj):
        return obj.child.name

    child_name.short_description = "Child"
    child_name.admin_order_field = "child__name"

    def save_model(self, request, obj, form, change):
        if "password" in form.changed_data and obj.password:
            obj.password = make_password(obj.password)
        super().save_model(request, obj, form, change)


@admin.register(ChildSubject)
class ChildSubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "child_name", "created_at"]
    search_fields = ["name", "child__name"]
    list_filter = ["created_at"]

    def child_name(self, obj):
        return obj.child.name

    child_name.short_description = "Child"


@admin.register(ChildTrait)
class ChildTraitAdmin(admin.ModelAdmin):
    list_display = ["name", "child_name", "created_at"]
    search_fields = ["name", "child__name"]
    list_filter = ["created_at"]

    def child_name(self, obj):
        return obj.child.name

    child_name.short_description = "Child"


@admin.register(ChildInterest)
class ChildInterestAdmin(admin.ModelAdmin):
    list_display = ["name", "child_name", "created_at"]
    search_fields = ["name", "child__name"]
    list_filter = ["created_at"]

    def child_name(self, obj):
        return obj.child.name

    child_name.short_description = "Child"


@admin.register(ChildDislike)
class ChildDislikeAdmin(admin.ModelAdmin):
    list_display = ["name", "child_name", "created_at"]
    search_fields = ["name", "child__name"]
    list_filter = ["created_at"]

    def child_name(self, obj):
        return obj.child.name

    child_name.short_description = "Child"
