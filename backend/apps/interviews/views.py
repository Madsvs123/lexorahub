"""Interview ViewSets: kits, panels, interviews, availability, scorecards."""

from __future__ import annotations

from django.utils.dateparse import parse_datetime
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.mixins import OrgQuerysetMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser

from . import services
from .models import Interview, InterviewerAvailability, InterviewKit, InterviewPanel, Scorecard
from .serializers import (
    AvailabilitySlotsSerializer,
    CancelInterviewSerializer,
    DecisionSummarySerializer,
    InterviewDecisionSummarySerializer,
    InterviewerAvailabilitySerializer,
    InterviewKitSerializer,
    InterviewListSerializer,
    InterviewPanelSerializer,
    InterviewSerializer,
    ScheduleInterviewSerializer,
    ScorecardSerializer,
    SubmitScorecardSerializer,
)


class InterviewFilter(filters.FilterSet):
    status = filters.CharFilter(field_name="status")
    interview_type = filters.CharFilter(field_name="interview_type")
    job = filters.UUIDFilter(field_name="job_id")
    candidate = filters.UUIDFilter(field_name="candidate_id")
    application = filters.UUIDFilter(field_name="application_id")
    start = filters.IsoDateTimeFilter(field_name="scheduled_start", lookup_expr="gte")
    end = filters.IsoDateTimeFilter(field_name="scheduled_start", lookup_expr="lte")

    class Meta:
        model = Interview
        fields = ["status", "interview_type", "job", "candidate", "application"]


class InterviewKitViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = InterviewKitSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "interviews.manage"
    queryset = InterviewKit.objects.select_related("job")
    search_fields = ("name", "description")

    def get_permissions(self):
        self.permission_required = (
            "interviews.view" if self.action in ("list", "retrieve") else "interviews.manage"
        )
        return super().get_permissions()


class InterviewPanelViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = InterviewPanelSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "interviews.manage"
    queryset = InterviewPanel.objects.prefetch_related("members")
    search_fields = ("name",)

    def get_permissions(self):
        self.permission_required = (
            "interviews.view" if self.action in ("list", "retrieve") else "interviews.manage"
        )
        return super().get_permissions()


class InterviewViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "interviews.view"
    filterset_class = InterviewFilter
    search_fields = ("notes", "location", "candidate__first_name", "candidate__last_name")
    ordering_fields = ("scheduled_start", "created_at", "status")
    queryset = Interview.objects.select_related(
        "job", "candidate", "organizer", "kit", "panel", "application"
    ).prefetch_related("assignments__interviewer", "scorecards__interviewer")

    def get_permissions(self):
        write = {
            "create", "update", "partial_update", "destroy", "schedule",
            "cancel", "submit_scorecard", "decision",
        }
        self.permission_required = (
            "interviews.manage" if self.action in write else "interviews.view"
        )
        return super().get_permissions()

    def get_serializer_class(self):
        return InterviewListSerializer if self.action == "list" else InterviewSerializer

    def perform_create(self, serializer):
        from apps.pipelines.models import Application
        from rest_framework.exceptions import ValidationError

        org = self.get_organization()
        application = serializer.validated_data["application"]
        if getattr(application, "organization_id", None) != org.id:
            application = Application.objects.for_org(org).filter(pk=application.pk).first()
            if application is None:
                raise ValidationError({"application": "Application not found."})
        interviewer_ids = self.request.data.get("interviewer_ids") or []
        interview = services.schedule_interview(
            organization=org,
            application=application,
            interview_type=serializer.validated_data.get(
                "interview_type", Interview.InterviewType.VIDEO
            ),
            scheduled_start=serializer.validated_data["scheduled_start"],
            scheduled_end=serializer.validated_data["scheduled_end"],
            organizer=self.request.user,
            kit=serializer.validated_data.get("kit"),
            panel=serializer.validated_data.get("panel"),
            location=serializer.validated_data.get("location", ""),
            meeting_link=serializer.validated_data.get("meeting_link", ""),
            notes=serializer.validated_data.get("notes", ""),
            interviewer_ids=interviewer_ids,
            actor=self.request.user,
        )
        serializer.instance = interview

    @action(detail=False, methods=["post"], url_path="schedule")
    def schedule(self, request):
        ser = ScheduleInterviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        from apps.pipelines.models import Application

        org = request.organization
        application = Application.objects.for_org(org).filter(pk=data["application"]).first()
        if application is None:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        kit = panel = None
        if data.get("kit"):
            kit = InterviewKit.objects.for_org(org).filter(pk=data["kit"]).first()
        if data.get("panel"):
            panel = InterviewPanel.objects.for_org(org).filter(pk=data["panel"]).first()
        interview = services.schedule_interview(
            organization=org,
            application=application,
            interview_type=data["interview_type"],
            scheduled_start=data["scheduled_start"],
            scheduled_end=data["scheduled_end"],
            organizer=request.user,
            kit=kit,
            panel=panel,
            location=data.get("location", ""),
            meeting_link=data.get("meeting_link", ""),
            notes=data.get("notes", ""),
            interviewer_ids=data.get("interviewer_ids") or [],
            actor=request.user,
        )
        return Response(
            InterviewSerializer(interview, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        interview = self.get_object()
        ser = CancelInterviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        interview = services.cancel_interview(
            interview=interview,
            actor=request.user,
            reason=ser.validated_data.get("reason", ""),
        )
        return Response(InterviewSerializer(interview, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path="calendar")
    def calendar(self, request):
        start_raw = request.query_params.get("start")
        end_raw = request.query_params.get("end")
        if not start_raw or not end_raw:
            return Response(
                {"detail": "start and end query parameters are required (ISO datetime)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start, end = parse_datetime(start_raw), parse_datetime(end_raw)
        if start is None or end is None:
            return Response(
                {"detail": "Invalid start or end datetime."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = (
            self.get_queryset()
            .filter(scheduled_start__gt=end, scheduled_end__gt=start)
            .exclude(status=Interview.Status.COMPLETED)
        )
        return Response(InterviewListSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="scorecard")
    def submit_scorecard(self, request, pk=None):
        interview = self.get_object()
        ser = SubmitScorecardSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        scorecard = services.submit_scorecard(
            interview=interview,
            interviewer=request.user,
            overall_rating=data["overall_rating"],
            recommendation=data["recommendation"],
            competency_scores=data.get("competency_scores"),
            answers=data.get("answers"),
            strengths=data.get("strengths", ""),
            concerns=data.get("concerns", ""),
        )
        return Response(ScorecardSerializer(scorecard).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="decision")
    def decision(self, request, pk=None):
        interview = self.get_object()
        if request.method == "GET":
            summary = getattr(interview, "decision_summary", None)
            if summary is None:
                return Response({"detail": "No decision summary yet."}, status=404)
            return Response(InterviewDecisionSummarySerializer(summary).data)
        ser = DecisionSummarySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        summary = services.compute_decision_summary(
            interview=interview,
            decided_by=request.user,
            decision=ser.validated_data.get("decision"),
            summary=ser.validated_data.get("summary", ""),
        )
        return Response(InterviewDecisionSummarySerializer(summary).data)


class InterviewerAvailabilityViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = InterviewerAvailabilitySerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "interviews.manage"
    queryset = InterviewerAvailability.objects.select_related("user")
    filterset_fields = ("user", "weekday")

    def get_permissions(self):
        self.permission_required = (
            "interviews.view"
            if self.action in ("list", "retrieve", "find_slots")
            else "interviews.manage"
        )
        return super().get_permissions()

    @action(detail=False, methods=["post"], url_path="find-slots")
    def find_slots(self, request):
        ser = AvailabilitySlotsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        slots = services.find_availability_slots(
            organization=request.organization,
            user_ids=data["user_ids"],
            start=data["start"],
            end=data["end"],
            duration_minutes=data.get("duration_minutes", 60),
            slot_step_minutes=data.get("slot_step_minutes", 30),
        )
        return Response({"slots": slots})


class ScorecardViewSet(OrgQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ScorecardSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "interviews.view"
    queryset = Scorecard.objects.select_related("interview", "interviewer")
    org_field = "interview__organization"

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if org is None:
            return Scorecard.objects.none()
        qs = self.queryset.filter(interview__organization=org)
        interview_id = self.request.query_params.get("interview")
        if interview_id:
            qs = qs.filter(interview_id=interview_id)
        return qs
