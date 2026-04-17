from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from common.response import APIResponse
from .services import AuthService
from .serializers import (
    RegisterSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    EmailPasswordLoginSerializer,
    GoogleLoginSerializer,
    AppleLoginSerializer,
    RefreshTokenSerializer,
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
    ChangePasswordSerializer,
    ProfileUpdateSerializer,
    UserProfileSerializer,
)

# from .throttles import (
#     RegisterThrottle,
#     LoginThrottle,
#     OTPResendThrottle,
#     OTPVerifyThrottle,
#     PasswordResetRequestThrottle,
# )
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.contrib.auth import get_user_model

User = get_user_model()


@extend_schema(tags=["01. Authentication"], summary="User Registration")
class RegisterView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    # throttle_classes = [RegisterThrottle]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            data = serializer.validated_data.copy()
            data.pop("confirm_password", None)

            user = AuthService.register_user(**data)
            return APIResponse.success(
                data={"user_id": str(user.id), "email": user.email},
                message="Registration successful. OTP sent to email.",
                status=201,
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=400)


@extend_schema(
    tags=["01. Authentication"], summary="Resend OTP for Registration or Password Reset"
)
class ResendOTPView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    # throttle_classes = [OTPResendThrottle]
    serializer_class = ResendOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = AuthService.resend_otp(**serializer.validated_data)
            return APIResponse.success(
                data={"email": user.email}, message="New OTP sent to your email."
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=400)


@extend_schema(
    tags=["01. Authentication"], summary="Verify OTP for Registration or Password Reset"
)
class VerifyOTPView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    # throttle_classes = [OTPVerifyThrottle]
    serializer_class = VerifyOTPSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        referral_code = request.data.get("referral_code")

        try:
            result = AuthService.verify_otp(
                email=serializer.validated_data["email"],
                otp_code=serializer.validated_data["otp"],
                otp_type=serializer.validated_data["otp_type"],
                referral_code=referral_code,  # pass it here
            )
            # ... rest of your response handling (same as before)
        except ValueError as e:
            return APIResponse.error(str(e), status=400)

        try:
            data = serializer.validated_data

            result = AuthService.verify_otp(
                email=data["email"],
                otp_code=data["otp"],
                otp_type=data["otp_type"],
            )
            if "access_token" in result:
                response = APIResponse.success(
                    data={
                        "access_token": result["access_token"],
                        "token_type": "Bearer",
                    },
                    message="Email verified. You are now logged in.",
                )
                response.set_cookie(
                    key="refresh_token",
                    value=result["refresh_token"],
                    httponly=True,
                    secure=True,
                    samesite="Strict",
                    max_age=7 * 24 * 3600,
                )
                return response
            else:
                return APIResponse.success(
                    data={"reset_token": result["reset_token"]},
                    message="OTP verified. Proceed to reset your password.",
                )
        except ValueError as e:
            return APIResponse.error(str(e), status=400)


@extend_schema(
    tags=["01. Authentication"],
    summary="Refresh Access Token using Refresh Token",
    description="Uses refresh_token from cookie automatically",
)
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return APIResponse.error("Refresh token missing", status=401)
        try:
            result = AuthService.refresh_access_token(refresh_token)
            response = APIResponse.success(
                data={"access_token": result["access_token"], "token_type": "Bearer"},
                message="Token refreshed.",
            )
            response.set_cookie(
                "refresh_token",
                result["refresh_token"],
                httponly=True,
                secure=True,
                samesite="Strict",
            )
            return response
        except ValueError as e:
            return APIResponse.error(str(e), status=401)


@extend_schema(
    tags=["01. Authentication"],
    summary="Login with Email & Password",
    request=EmailPasswordLoginSerializer,
    responses={
        200: OpenApiResponse(
            description="Login successful",
            response={
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "token_type": {"type": "string"},
                },
            },
        )
    },
)
class EmailLoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = EmailPasswordLoginSerializer
    # throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = AuthService.authenticate_with_email_password(
                serializer.validated_data["email"],
                serializer.validated_data["password"],
            )

            response = APIResponse.success(
                data={
                    "access_token": result["access_token"],
                    "token_type": "Bearer",
                },
                message="Login successful.",
            )

            response.set_cookie(
                "refresh_token",
                result["refresh_token"],
                httponly=True,
                secure=True,
                samesite="Strict",
            )
            return response

        except ValueError as e:
            return APIResponse.error(str(e), status=401)


#  Google Login
@extend_schema(
    tags=["01. Authentication"],
    summary="Login with Google",
    request=GoogleLoginSerializer,
)
class GoogleLoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = GoogleLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = AuthService.authenticate_with_google(
                serializer.validated_data["id_token"]
            )

            response = APIResponse.success(
                data={
                    "access_token": result["access_token"],
                    "token_type": "Bearer",
                },
                message="Login successful.",
            )

            response.set_cookie(
                "refresh_token",
                result["refresh_token"],
                httponly=True,
                secure=True,
                samesite="Strict",
            )
            return response

        except ValueError as e:
            return APIResponse.error(str(e), status=401)


#  Apple Login
@extend_schema(
    tags=["01. Authentication"],
    summary="Login with Apple",
    request=AppleLoginSerializer,
)
class AppleLoginView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = AppleLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = AuthService.authenticate_with_apple(
                serializer.validated_data["identity_token"],
                serializer.validated_data.get("full_name"),
            )

            response = APIResponse.success(
                data={
                    "access_token": result["access_token"],
                    "token_type": "Bearer",
                },
                message="Login successful.",
            )

            response.set_cookie(
                "refresh_token",
                result["refresh_token"],
                httponly=True,
                secure=True,
                samesite="Strict",
            )
            return response

        except ValueError as e:
            return APIResponse.error(str(e), status=401)


@extend_schema(
    tags=["01. Authentication"], summary="User Logout and Refresh Token Blacklisting"
)
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        AuthService.logout(refresh_token)
        response = APIResponse.success(message="Logged out successfully.")
        response.delete_cookie("refresh_token")
        return response


@extend_schema(tags=["02. Password Management"], summary="Request Password Reset OTP")
class PasswordResetRequestView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    # throttle_classes = [PasswordResetRequestThrottle]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AuthService.reset_password_request(serializer.validated_data["email"])
        # Always return success to prevent email enumeration
        return APIResponse.success(
            message="If your email is registered, you will receive a reset OTP."
        )


@extend_schema(tags=["02. Password Management"], summary="Reset Password using OTP")
class PasswordResetView(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            AuthService.reset_password(**serializer.validated_data)
            return APIResponse.success(
                message="Password reset successfully. Please log in."
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=400)


@extend_schema(
    tags=["02. Password Management"], summary="Change Password for Authenticated User"
)
class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            AuthService.change_password(request.user, **serializer.validated_data)
            # After password change, logout from all devices
            response = APIResponse.success(
                message="Password changed. Please log in again."
            )
            response.delete_cookie("refresh_token")
            return response
        except ValueError as e:
            return APIResponse.error(str(e), status=400)


@extend_schema(
    tags=["03. User Profile"],
    summary="Retrieve or Update User Profile",
    request=ProfileUpdateSerializer,
)
class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        serializer = ProfileUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if "full_name" in serializer.validated_data:
            user.full_name = serializer.validated_data["full_name"]
        if "profile_photo" in serializer.validated_data:
            user.profile_photo = serializer.validated_data["profile_photo"]
        user.save()
        return APIResponse.success(
            data=UserProfileSerializer(user).data, message="Profile updated."
        )

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return APIResponse.success(data=serializer.data)
