from django.urls import path
from .views import (
    RegisterView,
    ResendOTPView,
    VerifyOTPView,
    EmailLoginView,
    GoogleLoginView,
    AppleLoginView,
    TokenRefreshView,
    LogoutView,
    PasswordResetRequestView,
    PasswordResetView,
    ChangePasswordView,
    ProfileView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("login/email/", EmailLoginView.as_view(), name="email-login"),
    path("login/google/", GoogleLoginView.as_view(), name="google-login"),
    path("login/apple/", AppleLoginView.as_view(), name="apple-login"),
    path("token-refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "password-reset-request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path("password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("profile/", ProfileView.as_view(), name="profile"),
]
