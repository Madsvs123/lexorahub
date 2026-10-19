from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.scheduling.views import (
    CalendarEventViewSet,
    CampaignViewSet,
    ContentQueueViewSet,
    ScheduledPublicationViewSet,
)

router = DefaultRouter()
router.register("calendar", CalendarEventViewSet, basename="calendar")
router.register("queues", ContentQueueViewSet, basename="queue")
router.register("campaign", CampaignViewSet, basename="campaign")
router.register("schedules", ScheduledPublicationViewSet, basename="schedule")

urlpatterns = [path("", include(router.urls))]
