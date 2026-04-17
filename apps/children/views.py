from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from common.response import APIResponse
from .models import Child
from .serializers import (
    ChildCreateSerializer,
    ChildUpdateSerializer,
    ChildDetailSerializer,
    ChildListSerializer,
    ChildCredentialsUpdateSerializer,
    SubjectsUpdateSerializer,
    TraitsUpdateSerializer,
    InterestsUpdateSerializer,
    DislikesUpdateSerializer,
    AvatarUploadRequestSerializer,
    AvatarUploadResponseSerializer,
    AvatarConfirmSerializer,
    ProfileIntelligenceSerializer,
    ChildLoginRequestSerializer,
    ChildLoginResponseSerializer,
)
from .services import ChildService
from .selectors import (
    get_active_children_for_parent,
    get_child_by_id,
    get_child_profile_intelligence,
    get_child_profile_intelligence_internal,
)
from .permissions import IsChildOwner, IsInternalOrChildOwner
from .throttles import (
    ChildCreateThrottle,
    ChildUpdateThrottle,
    AvatarUploadThrottle,
    AttributeUpdateThrottle,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter


@extend_schema(tags=["04. children"], summary="Manage child profiles")
class ChildListCreateView(generics.GenericAPIView):
    """List all active children or create a new child profile."""

    permission_classes = [IsAuthenticated]

    def get_throttles(self):
        if self.request.method == "POST":
            return [ChildCreateThrottle()]
        return []

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ChildCreateSerializer
        return ChildListSerializer

    def get(self, request):
        """List all active children for the authenticated parent."""
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        children = get_active_children_for_parent(request.user)
        total = children.count()
        children = children[offset : offset + limit]

        serializer = ChildListSerializer(children, many=True)

        return APIResponse.success(
            data={
                "count": total,
                "limit": limit,
                "offset": offset,
                "results": serializer.data,
            },
            message="Children retrieved successfully.",
        )

    def post(self, request):
        """Create a new child profile."""
        serializer = ChildCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            child = ChildService.create_child(
                parent=request.user, data=serializer.validated_data
            )
            response_serializer = ChildDetailSerializer(child)
            return APIResponse.success(
                data=response_serializer.data,
                message="Child profile created successfully.",
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            error_status = (
                status.HTTP_409_CONFLICT
                if "email already in use" in str(e)
                else status.HTTP_400_BAD_REQUEST
            )
            return APIResponse.error(str(e), status=error_status)


@extend_schema(
    tags=["04. children"], summary="Retrieve, update, or delete a child profile"
)
class ChildDetailView(generics.GenericAPIView):
    """Retrieve, update, or delete a child profile."""

    permission_classes = [IsAuthenticated, IsChildOwner]

    def get_throttles(self):
        if self.request.method == "PATCH":
            return [ChildUpdateThrottle()]
        return []

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ChildUpdateSerializer
        return ChildDetailSerializer

    def get_child(self, child_id, request):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def get(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = ChildDetailSerializer(child)
        return APIResponse.success(data=serializer.data)

    def patch(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = ChildUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            updated_child = ChildService.update_child(
                child=child,
                name=serializer.validated_data.get("name"),
                age=serializer.validated_data.get("age"),
            )
            response_serializer = ChildDetailSerializer(updated_child)
            return APIResponse.success(
                data=response_serializer.data,
                message="Child profile updated successfully.",
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        try:
            ChildService.delete_child(child)
            return APIResponse.success(
                message="Child profile deactivated successfully."
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["04. children"], summary="Update child login credentials (email/password)"
)
class ChildCredentialsView(generics.GenericAPIView):
    """Update child login credentials."""

    permission_classes = [IsAuthenticated, IsChildOwner]
    serializer_class = ChildCredentialsUpdateSerializer

    def get_child(self, child_id, request):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def patch(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_profile = ChildService.update_credentials(
                child=child,
                email=serializer.validated_data.get("email"),
                password=serializer.validated_data.get("password"),
            )
            return APIResponse.success(
                data={
                    "child_id": str(child.id),
                    "email": updated_profile.email,
                    "is_email_verified": updated_profile.is_email_verified,
                },
                message="Child login credentials updated successfully.",
            )
        except ValueError as e:
            error_status = (
                status.HTTP_409_CONFLICT
                if "already in use" in str(e)
                else status.HTTP_400_BAD_REQUEST
            )
            return APIResponse.error(str(e), status=error_status)


@extend_schema(
    tags=["04. children"], summary="Replace entire subjects list for a child"
)
class ChildSubjectsView(generics.GenericAPIView):
    """Replace entire subjects list for a child."""

    permission_classes = [IsAuthenticated, IsChildOwner]
    throttle_classes = [AttributeUpdateThrottle]
    serializer_class = SubjectsUpdateSerializer

    def get_child(self, child_id, request):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def patch(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        count = ChildService.update_subjects(
            child, serializer.validated_data["subjects"]
        )

        return APIResponse.success(
            data={
                "child_id": str(child.id),
                "subjects": serializer.validated_data["subjects"],
                "count": count,
            },
            message="Subjects updated successfully.",
        )


@extend_schema(
    tags=["04. children"], summary="Replace entire personality traits list for a child"
)
class ChildTraitsView(generics.GenericAPIView):
    """Replace entire traits list for a child."""

    permission_classes = [IsAuthenticated, IsChildOwner]
    throttle_classes = [AttributeUpdateThrottle]
    serializer_class = TraitsUpdateSerializer

    def get_child(self, child_id, request):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def patch(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        count = ChildService.update_traits(child, serializer.validated_data["traits"])

        return APIResponse.success(
            data={
                "child_id": str(child.id),
                "traits": serializer.validated_data["traits"],
                "count": count,
            },
            message="Personality traits updated successfully.",
        )


@extend_schema(
    tags=["04. children"], summary="Replace entire interests list for a child"
)
class ChildInterestsView(generics.GenericAPIView):
    """Replace entire interests list for a child."""

    permission_classes = [IsAuthenticated, IsChildOwner]
    throttle_classes = [AttributeUpdateThrottle]
    serializer_class = InterestsUpdateSerializer

    def get_child(self, child_id, request):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def patch(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        count = ChildService.update_interests(
            child, serializer.validated_data["interests"]
        )

        return APIResponse.success(
            data={
                "child_id": str(child.id),
                "interests": serializer.validated_data["interests"],
                "count": count,
            },
            message="Interests updated successfully.",
        )


@extend_schema(
    tags=["04. children"], summary="Replace entire dislikes list for a child"
)
class ChildDislikesView(generics.GenericAPIView):
    """Replace entire dislikes list for a child."""

    permission_classes = [IsAuthenticated, IsChildOwner]
    throttle_classes = [AttributeUpdateThrottle]
    serializer_class = DislikesUpdateSerializer

    def get_child(self, child_id, request):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def patch(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        count = ChildService.update_dislikes(
            child, serializer.validated_data["dislikes"]
        )

        return APIResponse.success(
            data={
                "child_id": str(child.id),
                "dislikes": serializer.validated_data["dislikes"],
                "count": count,
            },
            message="Dislikes updated successfully.",
        )


@extend_schema(
    tags=["04. children"],
    summary="Generate presigned URL for avatar upload or confirm upload",
)
class ChildAvatarView(APIView):
    """Generate presigned URL for avatar upload or confirm upload."""

    permission_classes = [IsAuthenticated, IsChildOwner]

    def get_throttles(self):
        if self.request.method == "POST":
            return [AvatarUploadThrottle()]
        return []

    def get_child(self, child_id, request):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def post(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = AvatarUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = ChildService.generate_avatar_presigned_url(
                child, serializer.validated_data["content_type"]
            )
            response_serializer = AvatarUploadResponseSerializer(result)
            return APIResponse.success(
                data=response_serializer.data, message="Presigned upload URL generated."
            )
        except Exception as e:
            return APIResponse.error(
                str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request, child_id):
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = AvatarConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated_child = ChildService.confirm_avatar(
                child, serializer.validated_data["avatar_key"]
            )
            return APIResponse.success(
                data={"avatar_url": updated_child.avatar_url},
                message="Avatar uploaded successfully.",
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["04. children"],
    summary="Get child profile intelligence for AI pipeline",
    description="Allows either parent JWT or internal service key.",
    responses={
        200: ProfileIntelligenceSerializer,
        404: OpenApiResponse(description="Child profile not found."),
        401: OpenApiResponse(description="Unauthorized - invalid credentials."),
    },
)
class ChildProfileIntelligenceView(generics.GenericAPIView):
    """
    Get child profile intelligence for AI pipeline.
    Allows either parent JWT or internal service key.
    """

    permission_classes = [IsInternalOrChildOwner]
    serializer_class = ProfileIntelligenceSerializer

    def get(self, request, child_id):
        # Check if internal key is present
        internal_key = request.headers.get("X-Internal-Service-Key")
        from django.conf import settings

        if internal_key == getattr(settings, "INTERNAL_SERVICE_KEY", None):
            # Internal service call - no parent check
            data = get_child_profile_intelligence_internal(child_id)
        else:
            # Parent-scoped call
            data = get_child_profile_intelligence(child_id, request.user)

        if data is None:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(data)
        return APIResponse.success(
            data=serializer.data,
            message="Child profile intelligence retrieved successfully.",
        )


@extend_schema(
    tags=["04. children"],
    summary="Get call history for a specific child",
    description="Returns paginated call history with character details.",
    parameters=[
        OpenApiParameter(
            name="limit",
            type=int,
            description="Number of records to return (default: 50)",
            required=False,
        ),
        OpenApiParameter(
            name="offset",
            type=int,
            description="Number of records to skip for pagination (default: 0)",
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Call history retrieved successfully.",
            content=CallSessionSerializer(many=True),
        ),
        404: OpenApiResponse(description="Child profile not found."),
        401: OpenApiResponse(description="Unauthorized - invalid credentials."),
        501: OpenApiResponse(description="Call history feature is not available yet."),
    },
)
class ChildCallHistoryView(generics.GenericAPIView):
    """Get call history for a specific child."""

    permission_classes = [IsAuthenticated, IsChildOwner]

    def get(self, request, child_id):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        try:
            from apps.calls.models import CallSession
            from apps.calls.serializers import CallSessionSerializer
        except ImportError:
            return APIResponse.error(
                "Call history feature is not available yet.",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        calls = (
            CallSession.objects.filter(child=child, status="completed")
            .select_related("character")
            .order_by("-started_at")
        )

        total = calls.count()
        calls = calls[offset : offset + limit]

        serializer = CallSessionSerializer(calls, many=True)

        return APIResponse.success(
            data={
                "child_id": str(child.id),
                "child_name": child.name,
                "total_calls": total,
                "limit": limit,
                "offset": offset,
                "calls": serializer.data,
            },
            message="Call history retrieved successfully.",
        )


@extend_schema(
    tags=["04. children"],
    summary="Get achievements and learning stats for a child",
    description="Returns achievements, badges, and learning progress for the child.",
    responses={
        200: OpenApiResponse(
            description="Achievements retrieved successfully.",
            content=ChildAchievementsSerializer(),
        ),
        404: OpenApiResponse(description="Child profile not found."),
        401: OpenApiResponse(description="Unauthorized - invalid credentials."),
        501: OpenApiResponse(description="Achievements feature is not available yet."),
    },
)
class ChildAchievementsView(generics.GenericAPIView):
    """Get achievements and learning stats for a child."""

    permission_classes = [IsAuthenticated, IsChildOwner]

    def get(self, request, child_id):
        child = get_child_by_id(child_id, request.user)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        try:
            from apps.calls.selectors import get_achievements_for_child
        except ImportError:
            return APIResponse.error(
                "Achievements feature is not available yet.",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        achievements = get_achievements_for_child(child_id, request.user)

        if achievements is None:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        return APIResponse.success(
            data=achievements, message="Achievements retrieved successfully."
        )


# ========== Child Login View (for Authentication app) ==========


@extend_schema(
    tags=["04. children"],
    summary="Authenticate a child using email and password",
    description="This endpoint is public and used by the child-facing interface to log in.",
    request=ChildLoginRequestSerializer,
    responses={
        200: ChildLoginResponseSerializer,
        401: OpenApiResponse(description="Invalid email or password."),
    },
)
class ChildLoginView(APIView):
    """
    Authenticate a child using email and password.
    This endpoint is public and used by the child-facing interface.
    """

    permission_classes = []
    throttle_classes = [ChildLoginThrottle]
    serializer_class = ChildLoginRequestSerializer

    def post(self, request):
        serializer = ChildLoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        child = ChildService.authenticate_child(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if not child:
            return APIResponse.error(
                "Invalid email or password.", status=status.HTTP_401_UNAUTHORIZED
            )

        # Generate JWT token for child
        from apps.authentication.utils import (
            generate_access_token,
            generate_refresh_token,
        )

        # Create a user-like object for JWT payload
        class ChildUser:
            def __init__(self, child):
                self.id = child.id
                self.email = child.credentials.email
                self.role = "child"
                self.full_name = child.name
                self.pk = child.id  # Some JWT functions expect pk
                self.is_authenticated = True

        child_user = ChildUser(child)
        access_token = generate_access_token(child_user)
        refresh_token = generate_refresh_token(child_user)

        response_data = ChildLoginResponseSerializer(
            {
                "child_id": child.id,
                "name": child.name,
                "age": child.age,
                "avatar_url": child.avatar_url,
                "role": "child",
                "access_token": access_token,
                "token_type": "Bearer",
            }
        ).data

        response = APIResponse.success(data=response_data, message="Login successful.")

        # Set refresh token in HttpOnly cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=7 * 24 * 3600,
        )

        return response
