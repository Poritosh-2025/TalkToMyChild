from django.db.models import Subquery, OuterRef
from django.core.cache import cache
from .models import Child, ChildProfile
from .utils import get_child_cache_key, build_prompt_context


def get_child_by_id(child_id, parent):
    """Get a single child by ID with all attributes prefetched."""
    try:
        return (
            Child.objects.select_related("parent", "credentials")
            .prefetch_related("subjects", "traits", "interests", "dislikes")
            .get(id=child_id, parent=parent, is_active=True)
        )
    except Child.DoesNotExist:
        return None


def get_child_by_id_internal(child_id):
    """Get a single child by ID without parent check (for internal service)."""
    try:
        return Child.objects.prefetch_related(
            "subjects", "traits", "interests", "dislikes"
        ).get(id=child_id, is_active=True)
    except Child.DoesNotExist:
        return None


def get_child_profile_by_email(email):
    """Get child profile by email for authentication."""
    try:
        return (
            ChildProfile.objects.select_related("child")
            .prefetch_related(
                "child__subjects",
                "child__traits",
                "child__interests",
                "child__dislikes",
            )
            .get(email=email.lower())
        )
    except ChildProfile.DoesNotExist:
        return None


def get_active_children_for_parent(parent, include_last_call=True):
    """Get all active children with annotations."""
    children = Child.objects.filter(parent=parent, is_active=True).prefetch_related(
        "subjects", "traits", "interests", "dislikes", "credentials"
    )

    if include_last_call:
        try:
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
        except ImportError:
            pass  # Calls app not installed yet

    return children.order_by("-created_at")


def get_active_children_count(parent):
    """Get count of active children for a parent."""
    return Child.objects.filter(parent=parent, is_active=True).count()


def get_child_profile_intelligence(child_id, parent):
    """
    Get child profile intelligence payload for AI pipeline (parent-scoped).
    Uses caching to reduce database load.
    """
    cache_key = get_child_cache_key(child_id, "intelligence")
    cached_data = cache.get(cache_key)

    if cached_data:
        return cached_data

    child = get_child_by_id(child_id, parent)
    if not child:
        return None

    subjects = [s.name for s in child.subjects.all().order_by("name")]
    traits = [t.name for t in child.traits.all().order_by("name")]
    interests = [i.name for i in child.interests.all().order_by("name")]
    dislikes = [d.name for d in child.dislikes.all().order_by("name")]

    prompt_context = build_prompt_context(child, subjects, traits, interests, dislikes)

    data = {
        "child_id": child.id,
        "name": child.name,
        "age": child.age,
        "subjects": subjects,
        "traits": traits,
        "interests": interests,
        "dislikes": dislikes,
        "prompt_context": prompt_context,
    }

    # Cache for 5 minutes
    cache.set(cache_key, data, settings.CHILD_PROFILE_CACHE_TTL)

    return data


def get_child_profile_intelligence_internal(child_id):
    """
    Get child profile intelligence for internal service (no parent check).
    """
    cache_key = get_child_cache_key(child_id, "intelligence")
    cached_data = cache.get(cache_key)

    if cached_data:
        return cached_data

    child = get_child_by_id_internal(child_id)
    if not child:
        return None

    subjects = [s.name for s in child.subjects.all().order_by("name")]
    traits = [t.name for t in child.traits.all().order_by("name")]
    interests = [i.name for i in child.interests.all().order_by("name")]
    dislikes = [d.name for d in child.dislikes.all().order_by("name")]

    prompt_context = build_prompt_context(child, subjects, traits, interests, dislikes)

    data = {
        "child_id": child.id,
        "name": child.name,
        "age": child.age,
        "subjects": subjects,
        "traits": traits,
        "interests": interests,
        "dislikes": dislikes,
        "prompt_context": prompt_context,
    }

    cache.set(cache_key, data, settings.CHILD_PROFILE_CACHE_TTL)
    return data


def check_email_unique(email, exclude_child_id=None):
    """Check if email is unique across all child profiles."""
    queryset = ChildProfile.objects.filter(email=email.lower())
    if exclude_child_id:
        queryset = queryset.exclude(child_id=exclude_child_id)
    return not queryset.exists()
