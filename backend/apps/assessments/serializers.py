"""Serializers for assessments, ratings, and hiring comments."""

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import (
    AssessmentAnswer,
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentTemplate,
    CandidateRating,
    HiringComment,
)


class AssessmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentQuestion
        fields = (
            "id", "template", "prompt", "question_type", "options", "is_required",
            "is_knockout", "correct_answer", "points", "order", "created_at", "updated_at",
        )
        read_only_fields = ("id", "template", "created_at", "updated_at")


class AssessmentTemplateSerializer(serializers.ModelSerializer):
    questions = AssessmentQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = AssessmentTemplate
        fields = (
            "id", "organization", "name", "description", "assessment_type",
            "time_limit_minutes", "passing_score", "questions",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "organization", "created_by", "updated_by", "created_at", "updated_at", "questions"
        )


class AssessmentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentAnswer
        fields = (
            "id", "assignment", "question", "value", "is_correct", "points_awarded",
            "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "assignment", "is_correct", "points_awarded", "created_at", "updated_at"
        )


class AssessmentAssignmentSerializer(serializers.ModelSerializer):
    answers = AssessmentAnswerSerializer(many=True, read_only=True)
    template_detail = AssessmentTemplateSerializer(source="template", read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True, default="")
    job_title = serializers.CharField(source="job.title", read_only=True, default="")

    class Meta:
        model = AssessmentAssignment
        fields = (
            "id", "organization", "application", "candidate", "candidate_name", "job",
            "job_title", "template", "template_detail", "status", "due_at", "started_at",
            "submitted_at", "score", "passed", "knockout_failed", "answers",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "organization", "candidate", "job", "status", "started_at", "submitted_at",
            "score", "passed", "knockout_failed", "created_by", "updated_by",
            "created_at", "updated_at", "answers",
        )


class AssessmentAssignmentListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True, default="")
    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = AssessmentAssignment
        fields = (
            "id", "application", "candidate", "candidate_name", "job", "template",
            "template_name", "status", "due_at", "score", "passed", "knockout_failed", "created_at",
        )


class CandidateRatingSerializer(serializers.ModelSerializer):
    rater_detail = UserSerializer(source="rater", read_only=True)

    class Meta:
        model = CandidateRating
        fields = (
            "id", "organization", "application", "rater", "rater_detail", "overall",
            "criteria", "comment", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "rater", "created_at", "updated_at")


class HiringCommentSerializer(serializers.ModelSerializer):
    author_detail = UserSerializer(source="author", read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = HiringComment
        fields = (
            "id", "organization", "application", "author", "author_detail", "body",
            "mentions", "parent", "replies", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "organization", "author", "created_at", "updated_at", "replies"
        )

    def get_replies(self, obj):
        if obj.parent_id is None:
            return []
        return HiringCommentSerializer(
            obj.replies.select_related("author").all(), many=True, context=self.context
        ).data


class AssignAssessmentSerializer(serializers.Serializer):
    application = serializers.UUIDField()
    template = serializers.UUIDField()
    due_at = serializers.DateTimeField(required=False, allow_null=True)


class SubmitAnswersSerializer(serializers.Serializer):
    answers = serializers.ListField(child=serializers.DictField(), allow_empty=False)
    auto_score = serializers.BooleanField(default=False)
