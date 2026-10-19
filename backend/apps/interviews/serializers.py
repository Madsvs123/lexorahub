"""Serializers for interviews, kits, panels, scorecards, and availability."""

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import (
    Interview,
    InterviewDecisionSummary,
    InterviewerAssignment,
    InterviewerAvailability,
    InterviewKit,
    InterviewPanel,
    Scorecard,
)


class InterviewKitSerializer(serializers.ModelSerializer
    class Meta:
        model = InterviewKit
        fields = (
            "id", "organization", "name", "job", "description", "structured_questions",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "created_by", "updated_by", "created_at", "updated_at")


class InterviewPanelSerializer(serializers.ModelSerializer):
    members_detail = UserSerializer(source="members", many=True, read_only=True)

    class Meta:
        model = InterviewPanel
        fields = (
            "id", "organization", "name", "members", "members_detail",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "created_by", "updated_by", "created_at", "updated_at")


class InterviewerAssignmentSerializer(serializers.ModelSerializer):
    interviewer_detail = UserSerializer(source="interviewer", read_only=True)

    class Meta:
        model = InterviewerAssignment
        fields = (
            "id", "interview", "interviewer", "interviewer_detail", "role", "response",
            "feedback_submitted", "created_at", "updated_at",
        )
        read_only_fields = ("id", "interview", "feedback_submitted", "created_at", "updated_at")


class ScorecardSerializer(serializers.ModelSerializer):
    interviewer_detail = UserSerializer(source="interviewer", read_only=True)

    class Meta:
        model = Scorecard
        fields = (
            "id", "interview", "interviewer", "interviewer_detail", "overall_rating",
            "recommendation", "competency_scores", "answers", "strengths", "concerns",
            "submitted_at", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "interview", "interviewer", "submitted_at", "created_at", "updated_at"
        )


class InterviewDecisionSummarySerializer(serializers.ModelSerializer):
    decided_by_detail = UserSerializer(source="decided_by", read_only=True)

    class Meta:
        model = InterviewDecisionSummary
        fields = (
            "id", "interview", "decided_by", "decided_by_detail", "decision",
            "summary", "average_rating", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "interview", "decided_by", "average_rating", "created_at", "updated_at"
        )


class InterviewSerializer(serializers.ModelSerializer):
    assignments = InterviewerAssignmentSerializer(many=True, read_only=True)
    scorecards = ScorecardSerializer(many=True, read_only=True)
    decision_summary = InterviewDecisionSummarySerializer(read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True, default="")
    job_title = serializers.CharField(source="job.title", read_only=True, default="")
    organizer_detail = UserSerializer(source="organizer", read_only=True)
    interviewer_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )

    class Meta:
        model = Interview
        fields = (
            "id", "organization", "application", "job", "job_title", "candidate",
            "candidate_name", "interview_type", "status", "scheduled_start", "scheduled_end",
            "location", "meeting_link", "kit", "panel", "organizer", "organizer_detail",
            "notes", "interviewer_ids", "assignments", "scorecards", "decision_summary",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "organization", "status", "job", "candidate", "created_by", "updated_by",
            "created_at", "updated_at", "assignments", "scorecards", "decision_summary",
        )


class InterviewListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.email", read_only=True, default="")
    job_title = serializers.CharField(source="job.title", read_only=True, default="")

    class Meta:
        model = Interview
        fields = (
            "id", "application", "job", "job_title", "candidate", "candidate_name",
            "interview_type", "status", "scheduled_start", "scheduled_end", "location",
            "meeting_link", "organizer", "created_at",
        )


class InterviewerAvailabilitySerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source="user", read_only=True)

    class Meta:
        model = InterviewerAvailability
        fields = (
            "id", "organization", "user", "user_detail", "weekday", "start_time",
            "end_time", "timezone", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("start_time") or getattr(self.instance, "start_time", None)
        end = attrs.get("end_time") or getattr(self.instance, "end_time", None)
        if start and end and end <= start:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs


class ScheduleInterviewSerializer(serializers.Serializer):
    application = serializers.UUIDField()
    interview_type = serializers.ChoiceField(
        choices=Interview.InterviewType.choices, default=Interview.InterviewType.VIDEO
    )
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    kit = serializers.UUIDField(required=False, allow_null=True)
    panel = serializers.UUIDField(required=False, allow_null=True)
    location = serializers.CharField(required=False, allow_blank=True, default="")
    meeting_link = serializers.URLField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    interviewer_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )


class CancelInterviewSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class SubmitScorecardSerializer(serializers.Serializer):
    overall_rating = serializers.IntegerField(min_value=1, max_value=5)
    recommendation = serializers.ChoiceField(choices=Scorecard.Recommendation.choices)
    competency_scores = serializers.JSONField(required=False, default=dict)
    answers = serializers.JSONField(required=False, default=list)
    strengths = serializers.CharField(required=False, allow_blank=True, default="")
    concerns = serializers.CharField(required=False, allow_blank=True, default="")


class DecisionSummarySerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=InterviewDecisionSummary.Decision.choices, required=False
    )
    summary = serializers.CharField(required=False, allow_blank=True, default="")


class AvailabilitySlotsSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(default=60, min_value=15, max_value=480)
    slot_step_minutes = serializers.IntegerField(default=30, min_value=15, max_value=120)
