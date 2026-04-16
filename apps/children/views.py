from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.core.cache import cache
from django.db import transaction
from common.response import APIResponse
from .models import Child
from .serializers import (
    ChildCreateSerializer,
    ChildUpdateSerializer,
    ChildDetailSerializer,
    ChildListSerializer,
    AvatarUploadRequestSerializer,
    AvatarUploadResponseSerializer,
    AvatarConfirmSerializer,
    CallHistoryQuerySerializer,
    CallHistoryResponseSerializer,
    AchievementsResponseSerializer,
)
from .services import ChildService
from .selectors import (
    get_active_children_for_parent,
    get_child_by_id,
    get_child_with_details,
    search_children,
)
from .permissions import IsChildOwner
from .throttles import (
    ChildCreateThrottle,
    ChildUpdateThrottle,
    AvatarUploadThrottle,
    AvatarConfirmThrottle,
)
from drf_spectacular.utils import extend_schema, OpenApiResponse


@extend_schema(tags=["04. Children"], summary="List or Create Children")
class ChildListCreateView(generics.GenericAPIView):
    """
    List all active children or create a new child profile.

    GET: Returns paginated list of children
    POST: Creates a new child profile
    """

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
        # Get query parameters
        search_query = request.query_params.get("search", "")
        limit = int(request.query_params.get("limit", 50))
        offset = int(request.query_params.get("offset", 0))

        # Get children with optional search
        if search_query:
            children = search_children(request.user, search_query)
        else:
            children = get_active_children_for_parent(request.user)

        # Apply pagination
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
                parent=request.user,
                name=serializer.validated_data["name"],
                age=serializer.validated_data["age"],
            )
            response_serializer = ChildDetailSerializer(child)
            return APIResponse.success(
                data=response_serializer.data,
                message="Child profile created successfully.",
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=["04. Children"], summary="Retrieve, Update, or Delete a Child Profile"
)
class ChildDetailView(generics.GenericAPIView):
    """
    Retrieve, update, or delete a child profile.
    """

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
        """Helper to get and validate child."""
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def get(self, request, child_id):
        """Retrieve a single child profile."""
        child = self.get_child(child_id, request)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        # Use detail view with additional data
        child_with_details = get_child_with_details(child_id, request.user)
        serializer = ChildDetailSerializer(child_with_details)

        return APIResponse.success(data=serializer.data)

    def patch(self, request, child_id):
        """Update child profile (partial update)."""
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
        """Soft delete a child profile."""
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
    tags=["04. Children"],
    summary="Generate Presigned URL for Avatar Upload or Confirm Upload",
)
class ChildAvatarView(APIView):
    """
    Generate presigned URL for avatar upload or confirm upload.

    POST: Generate presigned URL
    PUT: Confirm upload after client uploads to S3
    """

    permission_classes = [IsAuthenticated, IsChildOwner]

    def get_throttles(self):
        if self.request.method == "POST":
            return [AvatarUploadThrottle()]
        return [AvatarConfirmThrottle()]

    def get_child(self, child_id, request):
        """Helper to get and validate child."""
        child = get_child_by_id(child_id, request.user)
        if not child:
            return None
        self.check_object_permissions(request, child)
        return child

    def post(self, request, child_id):
        """Generate presigned URL for avatar upload."""
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
        except ValueError as e:
            return APIResponse.error(str(e), status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return APIResponse.error(
                f"Failed to generate upload URL: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, child_id):
        """Confirm avatar upload after client uploads to S3."""
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
        except Exception as e:
            return APIResponse.error(
                f"Failed to confirm avatar: {str(e)}",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(tags=["04. Children"], summary="Get Call History for a Child")
class ChildCallHistoryView(generics.GenericAPIView):
    """
    Get call history for a specific child.
    """

    permission_classes = [IsAuthenticated, IsChildOwner]

    def get(self, request, child_id):
        """Get paginated call history."""
        child = get_child_by_id(child_id, request.user)
        if not child:
            return APIResponse.error(
                "Child profile not found.", status=status.HTTP_404_NOT_FOUND
            )

        # Validate query parameters
        query_serializer = CallHistoryQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        limit = query_serializer.validated_data["limit"]
        offset = query_serializer.validated_data["offset"]

        # Lazy import to avoid circular dependency
        try:
            from apps.calls.models import CallSession
            from apps.calls.serializers import CallSessionSerializer
        except ImportError:
            return APIResponse.error(
                "Call history feature is not available yet.",
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )

        # Query calls with pagination
        calls = (
            CallSession.objects.filter(child=child, status="completed")
            .select_related("character")
            .order_by("-started_at")
        )

        total = calls.count()
        calls = calls[offset : offset + limit]

        # Serialize
        call_serializer = CallSessionSerializer(calls, many=True)

        # Prepare response
        response_data = {
            "child_id": str(child.id),
            "child_name": child.name,
            "total_calls": total,
            "limit": limit,
            "offset": offset,
            "calls": call_serializer.data,
        }

        return APIResponse.success(
            data=response_data, message="Call history retrieved successfully."
        )


@extend_schema(
    tags=["04. Children"], summary="Get Achievements and Learning Stats for a Child"
)
class ChildAchievementsView(generics.GenericAPIView):
    """
    Get achievements and learning stats for a child.
    Results are cached for 1 hour.
    """

    permission_classes = [IsAuthenticated, IsChildOwner]

    def get(self, request, child_id):
        """Get cached achievements data."""
        # Try cache first
        cache_key = f"achievements_{child_id}_{request.user.id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return APIResponse.success(
                data=cached_data,
                message="Achievements retrieved successfully (cached).",
            )

        # Lazy import to avoid circular dependency
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

        # Validate with serializer
        serializer = AchievementsResponseSerializer(achievements)

        # Cache for 1 hour
        cache.set(cache_key, serializer.data, 3600)

        return APIResponse.success(
            data=serializer.data, message="Achievements retrieved successfully."
        )


@extend_schema(tags=["04. Children"], summary="Search Children by Name")
class ChildSearchView(generics.GenericAPIView):
    """
    Search children by name.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Search for children matching query."""
        query = request.query_params.get("q", "")

        if len(query) < 2:
            return APIResponse.error(
                "Search query must be at least 2 characters.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        children = search_children(request.user, query)
        limit = int(request.query_params.get("limit", 20))
        children = children[:limit]

        serializer = ChildListSerializer(children, many=True)

        return APIResponse.success(
            data={"query": query, "count": len(children), "results": serializer.data},
            message="Search completed.",
        )
