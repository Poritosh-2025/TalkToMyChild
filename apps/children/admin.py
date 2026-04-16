from django.contrib import admin
from django.utils.html import format_html
from .models import Child


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
        "updated_at",
    ]
    list_filter = ["is_active", "age", "created_at"]
    search_fields = ["name", "parent__email", "parent__full_name"]
    raw_id_fields = ["parent"]
    readonly_fields = ["id", "created_at", "updated_at", "avatar_preview"]
    actions = ["soft_delete_selected", "restore_selected"]

    fieldsets = (
        ("Basic Information", {"fields": ("id", "name", "age", "parent")}),
        ("Profile", {"fields": ("avatar", "avatar_preview", "is_active")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def parent_email(self, obj):
        return obj.parent.email

    parent_email.short_description = "Parent Email"
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
        count = 0
        for child in queryset:
            if child.is_active:
                child.soft_delete()
                count += 1
        self.message_user(request, f"{count} child profile(s) soft-deleted.")

    soft_delete_selected.short_description = "Soft delete selected children"

    def restore_selected(self, request, queryset):
        count = 0
        for child in queryset:
            if not child.is_active:
                # Check name uniqueness before restore
                if not Child.objects.filter(
                    parent=child.parent, name__iexact=child.name, is_active=True
                ).exists():
                    child.restore()
                    count += 1
                else:
                    self.message_user(
                        request,
                        f"Cannot restore '{child.name}': name already exists.",
                        level="ERROR",
                    )
        self.message_user(request, f"{count} child profile(s) restored.")

    restore_selected.short_description = "Restore selected children"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("parent")
