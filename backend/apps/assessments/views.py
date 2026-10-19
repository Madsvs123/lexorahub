"""Assessment ViewSets with candidate answer submission."""

from __future__ import annotations

from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.mixins import OrgQuerysetMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser

from . import services
from .models import (
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentTemplate,
    CandidateRating,
    HiringComment,
)
from .serializers import (
    AssessmentAssignmentListSerializer,
    AssessmentAssignmentSerializer,
    AssessmentQuestionSerializer,
    AssessmentTemplateSerializer,
    AssignAssessmentSerializer,
    CandidateRatingSerializer,
    HiringCommentSerializer,
    SubmitAnswersSerializer,
)


class AssessmentTemplateViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = AssessmentTemplateSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "assessments.manage"
    queryset = AssessmentTemplate.objects.prefetch_related("questions")
    search_fields = ("name", "description")
    filterset_fields = ("assessment_type",)

    def get_permissions(self):
        self.permission_required = (
            "assessments.view" if self.action in ("list", "retrieve") else "assessments.manage"
        )
        return super().get_permissions()


class AssessmentQuestionViewSet(viewsets.ModelViewSet):
    serializer_class = AssessmentQuestionSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "assessments.manage"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_template(self):
        from rest_framework.exceptions import NotFound

        org = getattr(self.request, "organization", None)
        qs = AssessmentTemplate.objects.all()
        if org is not None:
            qs = qs.for_org(org)
        template = qs.filter(pk=self.kwargs.get("template_pk")).first()
        if template is None:
            raise NotFound("Assessment template not found.")
        return template

    def get_queryset(self):
        return AssessmentQuestion.objects.filter(template=self.get_template())

    def get_permissions(self):
        self.permission_required = (
            "assessments.view" if self.action in ("list", "retrieve") else "assessments.manage"
        )
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(template=self.get_template())


class AssessmentAssignmentFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    application = filters.UUIDFilter(field_name="application_id")
    job = filters.UUIDFilter(field_name="job_id")
    candidate = filters.UUIDFilter(field_name="candidate_id")
    template = filters.UUIDFilter(field_name="template_id")

    class Meta:
        model = AssessmentAssignment
        fields = ["status", "application", "job", "candidate", "template"]


class AssessmentAssignmentViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "assessments.view"
    filterset_class = AssessmentAssignmentFilter
    queryset = AssessmentAssignment.objects.select_related(
        "template", "candidate", "job", "application"
    ).prefetch_related("answers__question", "template__questions")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        write = {"create", "assign", "score", "partial_update", "submit_answers"}
        self.permission_required = (
            "assessments.manage" if self.action in write else "assessments.view"
        )
        return super().get_permissions()

    def get_serializer_class(self):
        return (
            AssessmentAssignmentListSerializer
            if self.action == "list"
            else AssessmentAssignmentSerializer
        )

    def create(self, request, *args, **kwargs):
        return self.assign(request)

    @action(detail=False, methods=["post"], url_path="assign")
    def assign(self, request):
        ser = AssignAssessmentSerializer(data=request.data
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        from apps.pipelines.models import Application

        org = request.organization
        application = Application.objects.for_org(org).filter(pk=data["application"]).first()
        template = AssessmentTemplate.objects.for_org(org).filter(pk=data["template"]).first()
        if application is None:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        if template is None:
            return Response({"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
        assignment = services.assign_assessment(
            organization=org,
            application=application,
            template=template,
            due_at=data.get("due_at"),
            actor=request.user,
        )
        return Response(
            AssessmentAssignmentSerializer(assignment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="submit-answers")
    def submit_answers(self, request, pk=None):
        assignment = self.get_object()
        ser = SubmitAnswersSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        assignment = services.submit_answers(
            assignment=assignment,
            answers=ser.validated_data["answers"],
            actor=request.user,
            auto_score=ser.validated_data.get("auto_score", False),
        )
        return Response(
            AssessmentAssignmentSerializer(assignment, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="score")
    def score(self, request, pk=None):
        assignment = self.get_object()
        assignment = services.score_assignment(assignment=assignment, actor=request.user)
        return Response(
            AssessmentAssignmentSerializer(assignment, context={"request": request}).data
        )


class CandidateRatingViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = CandidateRatingSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "assessments.manage"
    queryset = CandidateRating.objects.select_related("rater", "application")
    filterset_fields = ("application",)

    def get_permissions(self):
        self.permission_required = (
            "assessments.view" if self.action in ("list", "retrieve") else "assessments.manage"
        )
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(organization=self.get_organization(), rater=self.request.user)


class HiringCommentViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = HiringCommentSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "assessments.manage"
    queryset = HiringComment.objects.select_related("author").prefetch_related("replies")
    filterset_fields = ("application", "parent")
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        self.permission_required = (
            "assessments.view" if self.action in ("list", "retrieve") else "assessments.manage"
        )
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        if "parent" not in self.request.query_params and self.action == "list":
            qs = qs.filter(parent__isnull=False)
        return qs

    def perform_create(self, serializer):
        comment = serializer.save(
            organization=self.get_organization(), author=self.request.user
        )
        services.add_mention_notifications(comment=comment, actor=self.request.user)
