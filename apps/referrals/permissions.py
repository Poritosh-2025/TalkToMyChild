from rest_framework.permissions import BasePermission
from django.conf import settings


class IsAuthenticatedUser(BasePermission):
    """Allow access only to authenticated users."""

    message = "Authentication required to access referral features."

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsInternalService(BasePermission):
    """
    Allow access only to internal service calls.
    Uses internal service key header for authentication.
    """

    message = "This endpoint is for internal use only."

    def has_permission(self, request, view):
        internal_key = request.headers.get("X-Internal-Service-Key")
        expected_key = getattr(settings, "INTERNAL_SERVICE_KEY", None)

        # Also allow if user is superadmin (for testing)
        if (
            request.user
            and request.user.is_authenticated
            and request.user.role == "superadmin"
        ):
            return True

        return internal_key and internal_key == expected_key
