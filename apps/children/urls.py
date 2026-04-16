from django.urls import path
from .views import (
    ChildListCreateView,
    ChildDetailView,
    ChildAvatarView,
    ChildCallHistoryView,
    ChildAchievementsView,
    ChildSearchView,
)

urlpatterns = [
    # Core CRUD endpoints
    path("", ChildListCreateView.as_view(), name="child-list-create"),
    path("<uuid:child_id>/", ChildDetailView.as_view(), name="child-detail"),
    # Avatar endpoints
    path("<uuid:child_id>/avatar/", ChildAvatarView.as_view(), name="child-avatar"),
    # Related data endpoints
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
    # Search endpoint
    path("search/", ChildSearchView.as_view(), name="child-search"),
]
