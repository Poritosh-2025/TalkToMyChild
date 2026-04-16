from django.db.models import Subquery, OuterRef, Q, F, Count, Sum, Avg, Max
from django.utils import timezone
from datetime import timedelta
from .models import Child


def get_child_by_id(child_id, parent):
    """
    Get a single child by ID, ensuring it belongs to the parent.
    Uses select_related to avoid N+1 queries for parent data.

    Returns Child instance or None.
    """
    try:
        return Child.objects.select_related("parent").get(
            id=child_id, parent=parent, is_active=True
        )
    except Child.DoesNotExist:
        return None


def get_child_by_id_including_inactive(child_id, parent):
    """
    Get a child by ID including inactive ones (for admin/recovery purposes).
    """
    try:
        return Child.objects.select_related("parent").get(id=child_id, parent=parent)
    except Child.DoesNotExist:
        return None


def get_active_children_for_parent(parent, include_last_call=True):
    """
    Get all active children for a parent with last_call_at annotation.
    Optimized with single query + subquery for last call timestamp.
    Prevents N+1 queries.
    """
    children = Child.objects.filter(parent=parent, is_active=True).order_by(
        "-created_at"
    )

    if include_last_call:
        # Lazy import to avoid circular dependency
        from apps.calls.models import CallSession

        children = children.annotate(
            last_call_at=Subquery(
                CallSession.objects.filter(
                    child=OuterRef("pk"), status="completed", ended_at__isnull=False
                )
                .order_by("-ended_at")
                .values("ended_at")[:1]
            )
        )

    return children


def get_active_children_count(parent):
    """Get count of active children for a parent."""
    return Child.objects.filter(parent=parent, is_active=True).count()


def get_child_with_details(child_id, parent):
    """
    Get child with all related data for detail view.
    Uses select_related for parent, prefetch for calls.
    """
    child = get_child_by_id(child_id, parent)
    if not child:
        return None

    # Annotate with last call timestamp
    from apps.calls.models import CallSession

    child.last_call_at = (
        CallSession.objects.filter(child=child, status="completed")
        .order_by("-ended_at")
        .values_list("ended_at", flat=True)
        .first()
    )

    return child


def get_child_names_by_parent(parent):
    """Get a dict of child IDs to names for the parent (cached)."""
    return {
        str(child.id): child.name
        for child in Child.objects.filter(parent=parent, is_active=True).only(
            "id", "name"
        )
    }


def search_children(parent, query):
    """Search children by name (case-insensitive)."""
    if not query:
        return get_active_children_for_parent(parent)

    return Child.objects.filter(
        parent=parent, is_active=True, name__icontains=query
    ).order_by("name")
