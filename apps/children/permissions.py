from rest_framework.permissions import BasePermission
from django.conf import settings


class IsChildOwner(BasePermission):
    """
    Permission that allows access only if the child belongs to the authenticated parent.
    """

    message = "You do not have permission to access this child profile."

    def has_object_permission(self, request, view, obj):
        return obj.parent == request.user


class IsInternalOrChildOwner(BasePermission):
    """
    Allows access if request has internal service key OR user is child's parent.
    Used for AI pipeline endpoint.
    """

    message = "You do not have permission to access this child profile."

    def has_permission(self, request, view):
        # Internal service key check (no user required)
        internal_key = request.headers.get("X-Internal-Service-Key")
        if internal_key and internal_key == getattr(
            settings, "INTERNAL_SERVICE_KEY", None
        ):
            return True
        # Otherwise require authenticated user
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Internal service key bypasses object check
        internal_key = request.headers.get("X-Internal-Service-Key")
        if internal_key and internal_key == getattr(
            settings, "INTERNAL_SERVICE_KEY", None
        ):
            return True
        return obj.parent == request.user


class HasActiveSubscription(BasePermission):
    """Check if parent has an active subscription."""

    message = "Active subscription required for this feature."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Check subscription status (to be implemented)
        return True
