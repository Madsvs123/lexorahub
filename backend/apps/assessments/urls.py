"""Assessment URL routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssessmentAssignmentViewSet,
    AssessmentQuestionViewSet,
    AssessmentTemplateViewSet,
    CandidateRatingViewSet,
    HiringCommentViewSet,
)

router = DefaultRouter()
router.register(r"assessment-templates", AssessmentTemplateViewSet, basename="assessment-templates")
router.register(
    r"assessment-assignments", AssessmentAssignmentViewSet, basename="assessment-assignments"
)
router.register(r"candidate-ratings", CandidateRatingViewSet, basename="candidate-ratings")
router.register(r"hiring-comments", HiringCommentViewSet, basename="hiring-comments")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "assessment-templates/<uuid:template_pk>/questions/",
        AssessmentQuestionViewSet.as_view({"get": "list", "post": "create"}),
        name="assessment-questions-list",
    ),
    path(
        "assessment-templates/<uuid:template_pk>/questions/<uuid:pk>/",
        AssessmentQuestionViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="assessment-questions-detail",
    ),
]
