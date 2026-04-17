from rest_framework import serializers
from django.core.validators import MinLengthValidator
from .models import (
    Child,
    ChildProfile,
    ChildSubject,
    ChildTrait,
    ChildInterest,
    ChildDislike,
)
from .validators import validate_child_password, validate_attribute_name


# ========== Attribute Serializers ==========


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildSubject
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class TraitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildTrait
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildInterest
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class DislikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChildDislike
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


# ========== Credential Serializers ==========


class ChildCredentialsSerializer(serializers.ModelSerializer):
    """Serializer for child login credentials."""

    last_login = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ChildProfile
        fields = ["email", "is_email_verified", "last_login", "created_at"]
        read_only_fields = ["is_email_verified", "last_login", "created_at"]


class ChildCredentialsUpdateSerializer(serializers.Serializer):
    """Serializer for updating child credentials."""

    email = serializers.EmailField(required=False)
    password = serializers.CharField(
        required=False, validators=[validate_child_password]
    )

    def validate_email(self, value):
        if value:
            return value.lower()
        return value


# ========== Child Serializers ==========


class ChildCreateSerializer(serializers.Serializer):
    """Serializer for creating a new child profile with all attributes."""

    # Required fields
    name = serializers.CharField(max_length=100, validators=[MinLengthValidator(2)])
    age = serializers.IntegerField(min_value=1, max_value=17)
    email = serializers.EmailField()
    password = serializers.CharField(validators=[validate_child_password])

    # Optional profile intelligence
    subjects = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False, default=list
    )
    traits = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False, default=list
    )
    interests = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False, default=list
    )
    dislikes = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False, default=list
    )

    def validate_email(self, value):
        return value.lower()

    def validate_name(self, value):
        return value.strip()

    def validate_subjects(self, value):
        return [validate_attribute_name(v) for v in value]

    def validate_traits(self, value):
        return [validate_attribute_name(v) for v in value]

    def validate_interests(self, value):
        return [validate_attribute_name(v) for v in value]

    def validate_dislikes(self, value):
        return [validate_attribute_name(v) for v in value]


class ChildUpdateSerializer(serializers.Serializer):
    """Serializer for updating child profile (partial updates)."""

    name = serializers.CharField(
        max_length=100, validators=[MinLengthValidator(2)], required=False
    )
    age = serializers.IntegerField(min_value=1, max_value=17, required=False)

    def validate_name(self, value):
        if value:
            return value.strip()
        return value


class ChildDetailSerializer(serializers.ModelSerializer):
    """Serializer for returning child details with all attributes."""

    avatar_url = serializers.SerializerMethodField()
    credentials = ChildCredentialsSerializer(source="credentials", read_only=True)
    subjects = serializers.SerializerMethodField()
    traits = serializers.SerializerMethodField()
    interests = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()
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
            "credentials",
            "subjects",
            "traits",
            "interests",
            "dislikes",
            "last_call_at",
            "has_active_calls",
            "created_at",
            "updated_at",
        ]

    def get_avatar_url(self, obj):
        return obj.avatar_url

    def get_subjects(self, obj):
        return [s.name for s in obj.subjects.all().order_by("name")]

    def get_traits(self, obj):
        return [t.name for t in obj.traits.all().order_by("name")]

    def get_interests(self, obj):
        return [i.name for i in obj.interests.all().order_by("name")]

    def get_dislikes(self, obj):
        return [d.name for d in obj.dislikes.all().order_by("name")]

    def get_last_call_at(self, obj):
        return getattr(obj, "last_call_at", None)


class ChildListSerializer(serializers.ModelSerializer):
    """Serializer for listing children (lightweight for dashboard)."""

    avatar_url = serializers.SerializerMethodField()
    login_email = serializers.SerializerMethodField()
    last_call_at = serializers.SerializerMethodField()
    attribute_counts = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = [
            "id",
            "name",
            "age",
            "avatar_url",
            "login_email",
            "last_call_at",
            "attribute_counts",
        ]

    def get_avatar_url(self, obj):
        return obj.avatar_url

    def get_login_email(self, obj):
        if hasattr(obj, "credentials"):
            return obj.credentials.email
        return None

    def get_last_call_at(self, obj):
        return getattr(obj, "last_call_at", None)

    def get_attribute_counts(self, obj):
        return {
            "subjects": obj.subjects.count(),
            "traits": obj.traits.count(),
            "interests": obj.interests.count(),
            "dislikes": obj.dislikes.count(),
        }


# ========== Attribute Update Serializers ==========


class SubjectsUpdateSerializer(serializers.Serializer):
    subjects = serializers.ListField(
        child=serializers.CharField(max_length=100), required=True
    )

    def validate_subjects(self, value):
        return [validate_attribute_name(v) for v in set(value)]


class TraitsUpdateSerializer(serializers.Serializer):
    traits = serializers.ListField(
        child=serializers.CharField(max_length=100), required=True
    )

    def validate_traits(self, value):
        return [validate_attribute_name(v) for v in set(value)]


class InterestsUpdateSerializer(serializers.Serializer):
    interests = serializers.ListField(
        child=serializers.CharField(max_length=100), required=True
    )

    def validate_interests(self, value):
        return [validate_attribute_name(v) for v in set(value)]


class DislikesUpdateSerializer(serializers.Serializer):
    dislikes = serializers.ListField(
        child=serializers.CharField(max_length=100), required=True
    )

    def validate_dislikes(self, value):
        return [validate_attribute_name(v) for v in set(value)]


# ========== Avatar Serializers ==========


class AvatarUploadRequestSerializer(serializers.Serializer):
    content_type = serializers.CharField(max_length=50, default="image/jpeg")

    def validate_content_type(self, value):
        from .validators import validate_content_type

        validate_content_type(value)
        return value


class AvatarUploadResponseSerializer(serializers.Serializer):
    upload_url = serializers.URLField()
    avatar_key = serializers.CharField()
    expires_in = serializers.IntegerField()


class AvatarConfirmSerializer(serializers.Serializer):
    avatar_key = serializers.CharField(max_length=1024)

    def validate_avatar_key(self, value):
        from .validators import validate_s3_key

        validate_s3_key(value)
        return value


# ========== Profile Intelligence Serializer ==========


class ProfileIntelligenceSerializer(serializers.Serializer):
    """Serializer for AI pipeline payload."""

    child_id = serializers.UUIDField()
    name = serializers.CharField()
    age = serializers.IntegerField()
    subjects = serializers.ListField(child=serializers.CharField())
    traits = serializers.ListField(child=serializers.CharField())
    interests = serializers.ListField(child=serializers.CharField())
    dislikes = serializers.ListField(child=serializers.CharField())
    prompt_context = serializers.CharField()


# ========== Child Login Serializer (for Auth app) ==========


class ChildLoginRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class ChildLoginResponseSerializer(serializers.Serializer):
    child_id = serializers.UUIDField()
    name = serializers.CharField()
    age = serializers.IntegerField()
    avatar_url = serializers.CharField(allow_null=True)
    role = serializers.CharField(default="child")
    access_token = serializers.CharField()
    token_type = serializers.CharField(default="Bearer")
