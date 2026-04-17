from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.core.cache import cache
from common.response import APIResponse
from .models import Referral
from .serializers import (
    ReferralCodeResponseSerializer,
    ReferralListSerializer,
    ReferralStatsSerializer,
    ReferralRedeemRequestSerializer,
    ReferralRedeemResponseSerializer,
    ReferralCreateRequestSerializer,
    ReferralCheckEligibilityResponseSerializer,
)
from .services import ReferralService
from .selectors import (
    get_referrals_for_user,
    get_referral_stats_for_user,
    get_referral_code_for_user,
)
from .permissions import IsAuthenticatedUser, IsInternalService
from .throttles import (
    ReferralCreateThrottle,
    ReferralListThrottle,
    ReferralRedeemThrottle,
    ReferralCheckThrottle,
)


class MyReferralCodeView(generics.GenericAPIView):
    """
    Get the current user's referral code and sharing links.
    GET /api/v1/referrals/my-code/
    """

    permission_classes = [IsAuthenticatedUser]
    serializer_class = ReferralCodeResponseSerializer

    def get(self, request):
        referral_code_obj = ReferralService.get_referral_link(request.user)
        serializer = self.get_serializer(referral_code_obj)
        return APIResponse.success(
            data=serializer.data, message="Your referral code and sharing links."
        )


class ReferralListView(generics.GenericAPIView):
    """
    List all referrals sent by the current user.
    GET /api/v1/referrals/?status=PENDING&limit=20&offset=0
    """

    permission_classes = [IsAuthenticatedUser]
    throttle_classes = [ReferralListThrottle]
    serializer_class = ReferralListSerializer

    def get(self, request):
        # Get query parameters
        status_filter = request.query_params.get("status")
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))

        # Get referrals
        referrals = get_referrals_for_user(request.user, status_filter)

        # Apply pagination
        total = referrals.count()
        referrals = referrals[offset : offset + limit]

        serializer = self.get_serializer(referrals, many=True)

        return APIResponse.success(
            data={
                "count": total,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            },
            message="Referrals retrieved successfully.",
        )


class ReferralStatsView(generics.GenericAPIView):
    """
    Get aggregated referral statistics for the current user.
    GET /api/v1/referrals/stats/
    """

    permission_classes = [IsAuthenticatedUser]
    serializer_class = ReferralStatsSerializer

    def get(self, request):
        stats = get_referral_stats_for_user(request.user)
        serializer = self.get_serializer(stats)
        return APIResponse.success(
            data=serializer.data, message="Referral statistics retrieved successfully."
        )


class ReferralRedeemView(generics.GenericAPIView):
    """
    Redeem a referral code for a new user.
    Internal endpoint - called by Auth app after OTP verification.
    POST /api/v1/referrals/redeem/
    """

    permission_classes = [IsInternalService]
    throttle_classes = [ReferralRedeemThrottle]
    serializer_class = ReferralRedeemRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from django.contrib.auth import get_user_model

        User = get_user_model()

        try:
            new_user = User.objects.get(id=serializer.validated_data["new_user_id"])
        except User.DoesNotExist:
            return APIResponse.error(
                "User not found.", status=status.HTTP_404_NOT_FOUND
            )

        try:
            result = ReferralService.redeem_referral(
                referral_code=serializer.validated_data["referral_code"],
                new_user=new_user,
            )
            response_serializer = ReferralRedeemResponseSerializer(result)
            return APIResponse.success(
                data=response_serializer.data,
                message="Referral redeemed. Credits issued to both users.",
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)


class ReferralCreateView(generics.GenericAPIView):
    """
    Create a new referral invitation (send invite to email).
    POST /api/v1/referrals/invite/
    """

    permission_classes = [IsAuthenticatedUser]
    throttle_classes = [ReferralCreateThrottle]
    serializer_class = ReferralCreateRequestSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["user"] = self.request.user
        return context

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            referral = ReferralService.create_referral_invitation(
                referrer=request.user, email=serializer.validated_data["email"]
            )
            return APIResponse.success(
                data={
                    "id": str(referral.id),
                    "email": referral.referred_email,
                    "expires_at": referral.expires_at,
                    "status": referral.status,
                },
                message="Referral invitation sent successfully.",
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)


class ReferralCheckEligibilityView(APIView):
    """
    Check if a referral code is valid for a given email.
    Used during signup to validate referral code before submission.
    GET /api/v1/referrals/check/?code=ABC123&email=user@example.com
    """

    permission_classes = []  # Public endpoint
    throttle_classes = [ReferralCheckThrottle]

    def get(self, request):
        referral_code = request.query_params.get("code")
        email = request.query_params.get("email")

        if not referral_code or not email:
            return APIResponse.error(
                "Both 'code' and 'email' parameters are required.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = ReferralService.check_referral_eligibility(referral_code, email)
            serializer = ReferralCheckEligibilityResponseSerializer(result)
            return APIResponse.success(data=serializer.data, message=result["message"])
        except Exception as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)


class ReferralDetailView(generics.GenericAPIView):
    """
    Get details of a specific referral.
    GET /api/v1/referrals/{id}/
    """

    permission_classes = [IsAuthenticatedUser]
    serializer_class = ReferralListSerializer

    def get(self, request, referral_id):
        from .selectors import get_referral_by_id

        referral = get_referral_by_id(referral_id, request.user)

        if not referral:
            return APIResponse.error(
                "Referral not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(referral)
        return APIResponse.success(
            data=serializer.data, message="Referral details retrieved successfully."
        )


class ReferralResendInvitationView(APIView):
    """
    Resend a referral invitation (for expired or pending invitations).
    POST /api/v1/referrals/{id}/resend/
    """

    permission_classes = [IsAuthenticatedUser]
    throttle_classes = [ReferralCreateThrottle]

    def post(self, request, referral_id):
        from .selectors import get_referral_by_id

        referral = get_referral_by_id(referral_id, request.user)

        if not referral:
            return APIResponse.error(
                "Referral not found.", status=status.HTTP_404_NOT_FOUND
            )

        if referral.status == "COMPLETED":
            return APIResponse.error(
                "Cannot resend a completed referral.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create a new referral with same email
        try:
            new_referral = ReferralService.create_referral_invitation(
                referrer=request.user, email=referral.referred_email
            )
            return APIResponse.success(
                data={
                    "id": str(new_referral.id),
                    "email": new_referral.referred_email,
                    "expires_at": new_referral.expires_at,
                },
                message="Referral invitation resent successfully.",
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)
