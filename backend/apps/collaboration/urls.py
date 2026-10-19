from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.collaboration.views import CollaborationSessionViewSet, DocumentConflictViewSet

router = DefaultRouter()
router.register("sessions", CollaborationSessionViewSet, basename="collab-session")
router.register("conflict", DocumentConflictViewSet, basename="collab-conflict")

urlpatterns = [path("", include(router.urls))]
