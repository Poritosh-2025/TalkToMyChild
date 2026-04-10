from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match"}
            )
        return data


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    otp_type = serializers.ChoiceField(choices=["REGISTER_VERIFY", "PASSWORD_RESET"])


class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_type = serializers.ChoiceField(choices=["REGISTER_VERIFY", "PASSWORD_RESET"])


class EmailPasswordLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()


class AppleLoginSerializer(serializers.Serializer):
    identity_token = serializers.CharField()
    full_name = serializers.CharField(required=False, allow_blank=True)


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=False)  # will be taken from cookie


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        return data


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("New passwords do not match")
        return data


class ProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=100, required=False)
    profile_photo = serializers.URLField(required=False)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "profile_photo",
            "role",
            "is_email_verified",
            "credit_balance",
            "referral_code",
            "date_joined",
            "last_login",
        ]
