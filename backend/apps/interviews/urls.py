"""Interview URL routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    InterviewerAvailabilityViewSet,
    InterviewKitViewSet,
    InterviewPanelViewSet,
    InterviewViewSet,
    ScorecardViewSet,
)

router = DefaultRouter()
router.register(r"interview-kits", InterviewKitViewSet, basename="interview-kits")
router.register(r"interview-panels", InterviewPanelViewSet, basename="interview-panels")
router.register(r"interviews", InterviewViewSet, basename="interviews")
router.register(
    r"interviewer-availability",
    InterviewerAvailabilityViewSet,
    basename="interviewer-availability",
)
router.register(r"scorecards", ScorecardViewSet, basename="scorecards")

urlpatterns = [path("", include(router.urls))]
