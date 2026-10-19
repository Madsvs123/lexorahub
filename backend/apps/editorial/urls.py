from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.editorial.views import (
    AssignmentViewSet,
    CorrectionViewSet,
    EditorialCommentViewSet,
    EditorialNoteViewSet,
)

router = DefaultRouter()
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("comment", EditorialCommentViewSet, basename="editorial-comment")
router.register("notes", EditorialNoteViewSet, basename="editorial-note")
router.register("corrections", CorrectionViewSet, basename="correction")

urlpatterns = [path("", include(router.urls))]
