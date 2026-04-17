from django.urls import path
from .views import (
    ChildListCreateView,
    ChildDetailView,
    ChildCredentialsView,
    ChildSubjectsView,
    ChildTraitsView,
    ChildInterestsView,
    ChildDislikesView,
    ChildAvatarView,
    ChildProfileIntelligenceView,
    ChildCallHistoryView,
    ChildAchievementsView,
)

urlpatterns = [
    # Core CRUD
    path("", ChildListCreateView.as_view(), name="child-list-create"),
    path("<uuid:child_id>/", ChildDetailView.as_view(), name="child-detail"),
    # Credentials
    path(
        "<uuid:child_id>/credentials/",
        ChildCredentialsView.as_view(),
        name="child-credentials",
    ),
    # Profile intelligence attributes
    path(
        "<uuid:child_id>/subjects/", ChildSubjectsView.as_view(), name="child-subjects"
    ),
    path("<uuid:child_id>/traits/", ChildTraitsView.as_view(), name="child-traits"),
    path(
        "<uuid:child_id>/interests/",
        ChildInterestsView.as_view(),
        name="child-interests",
    ),
    path(
        "<uuid:child_id>/dislikes/", ChildDislikesView.as_view(), name="child-dislikes"
    ),
    # Avatar
    path("<uuid:child_id>/avatar/", ChildAvatarView.as_view(), name="child-avatar"),
    # AI pipeline
    path(
        "<uuid:child_id>/profile-intelligence/",
        ChildProfileIntelligenceView.as_view(),
        name="child-profile-intelligence",
    ),
    # Related data
    path(
        "<uuid:child_id>/call-history/",
        ChildCallHistoryView.as_view(),
        name="child-call-history",
    ),
    path(
        "<uuid:child_id>/achievements/",
        ChildAchievementsView.as_view(),
        name="child-achievements",
    ),
]
