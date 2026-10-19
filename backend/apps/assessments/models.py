"""
HireFlux assessments, assignments, answers, ratings, and hiring comments.
"""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import AuditedModel, TenantModel, TimeStampedModel


class AssessmentTemplate(TenantModel, AuditedModel):
    class AssessmentType(models.TextChoices):
        QUESTIONNAIRE = "questionnaire", "Questionnaire"
        SKILLS = "skills", "Skills"
        KNOCKOUT = "knockout", "Knockout"
        CUSTOM = "custom", "Custom"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    assessment_type = models.CharField(
        max_length=32,
        choices=AssessmentType.choices,
        default=AssessmentType.QUESTIONNAIRE,
    )
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True)
    passing_score = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_assessment_template_org_name",
            ),
        ]

    def __str__(self):
        return self.name


class AssessmentQuestion(TimeStampedModel):
    class QuestionType(models.TextChoices):
        TEXT = "text", "Text"
        SINGLE = "single", "Single choice"
        MULTI = "multi", "Multiple choice"
        YES_NO = "yes_no", "Yes / No"
        NUMBER = "number", "Number"
        RATING = "rating", "Rating"
        FILE = "file", "File"

    template = models.ForeignKey(
        AssessmentTemplate, on_delete=models.CASCADE, related_name="questions"
    )
    prompt = models.TextField()
    question_type = models.CharField(
        max_length=16, choices=QuestionType.choices, default=QuestionType.TEXT
    )
    options = models.JSONField(default=list, blank=True)
    is_required = models.BooleanField(default=False)
    is_knockout = models.BooleanField(default=False)
    correct_answer = models.JSONField(null=True, blank=True)
    points = models.DecimalField(max_digits=7, decimal_places=2, default=1)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "created_at")

    def __str__(self):
        return self.prompt[:80]


class AssessmentAssignment(TenantModel, AuditedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"
        SCORED = "scored", "Scored"
        EXPIRED = "expired", "Expired"

    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="assessment_assignments",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="assessment_assignments",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="assessment_assignments",
    )
    template = models.ForeignKey(
        AssessmentTemplate, on_delete=models.PROTECT, related_name="assignments"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    due_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    knockout_failed = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["application", "status"]),
        ]

    def __str__(self):
        return f"Assignment {self.pk} ({self.status})"


class AssessmentAnswer(TimeStampedModel):
    assignment = models.ForeignKey(
        AssessmentAssignment, on_delete=models.CASCADE, related_name="answers"
    )
    question = models.ForeignKey(
        AssessmentQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    value = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    points_awarded = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ("question__order", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "question"], name="uniq_assessment_answer"
            ),
        ]

    def __str__(self):
        return f"Answer {self.assignment_id}/{self.question_id}"


class CandidateRating(TenantModel, TimeStampedModel):
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="candidate_ratings",
    )
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="candidate_ratings",
    )
    overall = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    criteria = models.JSONField(default=dict, blank=True)
    comment = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "application", "rater"],
                name="uniq_candidate_rating_rater",
            ),
        ]

    def __str__(self):
        return f"Rating {self.application_id} by {self.rater_id}: {self.overall}"


class HiringComment(TenantModel, TimeStampedModel):
    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="hiring_comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hiring_comments",
    )
    body = models.TextField()
    mentions = models.JSONField(default=list, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Comment on {self.application_id} by {self.author_id}"
