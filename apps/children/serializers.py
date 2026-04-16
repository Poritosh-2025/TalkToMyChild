from rest_framework import serializers
from django.core.validators import MinLengthValidator
from .models import Child
from .validators import validate_s3_key


class ChildCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new child profile."""

    class Meta:
        model = Child
        fields = ["id", "name", "age", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        """Additional name validation."""
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError(
                "Name must be at least 2 characters long."
            )
        if len(value) > 100:
            raise serializers.ValidationError("Name must be less than 100 characters.")
        return value

    def validate_age(self, value):
        """Validate age range."""
        if not 1 <= value <= 17:
            raise serializers.ValidationError("Age must be between 1 and 17.")
        return value


class ChildUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating child profile (partial updates allowed)."""

    class Meta:
        model = Child
        fields = ["name", "age"]
        extra_kwargs = {"name": {"required": False}, "age": {"required": False}}

    def validate_name(self, value):
        if value:
            value = value.strip()
            if len(value) < 2:
                raise serializers.ValidationError(
                    "Name must be at least 2 characters long."
                )
        return value

    def validate_age(self, value):
        if value and not 1 <= value <= 17:
            raise serializers.ValidationError("Age must be between 1 and 17.")
        return value


class ChildDetailSerializer(serializers.ModelSerializer):
    """Serializer for returning child details with computed fields."""

    avatar_url = serializers.SerializerMethodField()
    last_call_at = serializers.SerializerMethodField()
    has_active_calls = serializers.BooleanField(read_only=True)

    class Meta:
        model = Child
        fields = [
            "id",
            "name",
            "age",
            "avatar_url",
            "is_active",
            "created_at",
            "updated_at",
            "last_call_at",
            "has_active_calls",
        ]

    def get_avatar_url(self, obj):
        return obj.avatar_url

    def get_last_call_at(self, obj):
        """Get last call timestamp from annotation."""
        return getattr(obj, "last_call_at", None)


class ChildListSerializer(serializers.ModelSerializer):
    """Serializer for listing children (lightweight)."""

    avatar_url = serializers.SerializerMethodField()
    last_call_at = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = ["id", "name", "age", "avatar_url", "last_call_at"]

    def get_avatar_url(self, obj):
        return obj.avatar_url

    def get_last_call_at(self, obj):
        return getattr(obj, "last_call_at", None)


class AvatarUploadRequestSerializer(serializers.Serializer):
    """Request serializer for generating presigned URL."""

    content_type = serializers.CharField(max_length=50, default="image/jpeg")

    def validate_content_type(self, value):
        from .validators import validate_content_type

        validate_content_type(value)
        return value


class AvatarUploadResponseSerializer(serializers.Serializer):
    """Response after generating presigned URL."""

    upload_url = serializers.URLField()
    avatar_key = serializers.CharField()
    expires_in = serializers.IntegerField()


class AvatarConfirmSerializer(serializers.Serializer):
    """Request serializer for confirming avatar upload."""

    avatar_key = serializers.CharField(max_length=1024, validators=[validate_s3_key])


class CallHistoryQuerySerializer(serializers.Serializer):
    """Query parameters for call history."""

    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)
    offset = serializers.IntegerField(min_value=0, default=0)


class CallHistoryEntrySerializer(serializers.Serializer):
    """Call history entry serializer (placeholder until calls app is ready)."""

    id = serializers.UUIDField()
    character_name = serializers.CharField()
    character_icon = serializers.CharField(required=False, allow_blank=True)
    duration_seconds = serializers.IntegerField()
    started_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField()
    status = serializers.CharField()


class CallHistoryResponseSerializer(serializers.Serializer):
    """Call history response structure."""

    child_id = serializers.UUIDField()
    child_name = serializers.CharField()
    total_calls = serializers.IntegerField()
    calls = CallHistoryEntrySerializer(many=True)


class SubjectAchievementSerializer(serializers.Serializer):
    """Subject achievement data."""

    name = serializers.CharField()
    hours = serializers.FloatField()
    goal = serializers.IntegerField()
    icon = serializers.CharField()
    progress_percentage = serializers.SerializerMethodField()

    def get_progress_percentage(self, obj):
        if obj.get("goal", 0) > 0:
            return min(100, int((obj.get("hours", 0) / obj["goal"]) * 100))
        return 0


class AchievementsResponseSerializer(serializers.Serializer):
    """Achievements response structure."""

    weekly_streak = serializers.IntegerField()
    check_in_days = serializers.CharField()
    total_usage_hours = serializers.FloatField()
    weekly_goal_hours = serializers.IntegerField()
    weekly_progress_percentage = serializers.SerializerMethodField()
    subjects = SubjectAchievementSerializer(many=True)

    def get_weekly_progress_percentage(self, obj):
        if obj.get("weekly_goal_hours", 0) > 0:
            return min(
                100,
                int((obj.get("total_usage_hours", 0) / obj["weekly_goal_hours"]) * 100),
            )
        return 0
