from rest_framework.permissions import BasePermission


class IsChildOwner(BasePermission):
    """
    Permission that allows access only if the child belongs to the authenticated user.
    This ensures proper tenant isolation.
    """

    message = "You do not have permission to access this child profile."

    def has_object_permission(self, request, view, obj):
        # obj is a Child instance
        return obj.parent == request.user


class HasActiveSubscription(BasePermission):
    """
    Permission that checks if parent has an active subscription.
    Used for premium features like achievements.
    """

    message = "Active subscription required for this feature."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Check if user has active subscription
        # This will be implemented when subscriptions app is ready
        from apps.subscriptions.selectors import has_active_subscription

        return has_active_subscription(request.user)
