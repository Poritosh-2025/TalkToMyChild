from django.urls import path
from .views import (
    MyReferralCodeView,
    ReferralListView,
    ReferralStatsView,
    ReferralRedeemView,
    ReferralCreateView,
    ReferralCheckEligibilityView,
    ReferralDetailView,
    ReferralResendInvitationView,
)

urlpatterns = [
    # Core endpoints
    path("my-code/", MyReferralCodeView.as_view(), name="my-referral-code"),
    path("", ReferralListView.as_view(), name="referral-list"),
    path("stats/", ReferralStatsView.as_view(), name="referral-stats"),
    path("invite/", ReferralCreateView.as_view(), name="referral-invite"),
    path("check/", ReferralCheckEligibilityView.as_view(), name="referral-check"),
    path("<uuid:referral_id>/", ReferralDetailView.as_view(), name="referral-detail"),
    path(
        "<uuid:referral_id>/resend/",
        ReferralResendInvitationView.as_view(),
        name="referral-resend",
    ),
    # Internal endpoint (not exposed in public API docs)
    path("redeem/", ReferralRedeemView.as_view(), name="referral-redeem"),
]
