"""
HireFlux interview kits, scheduling, panels, scorecards, and decisions.
"""

from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import AuditedModel, TenantModel, TimeStampedModel


class InterviewKit(TenantModel, AuditedModel):
    name = models.CharField(max_length=200)
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_kits",
    )
    description = models.TextField(blank=True, default="")
    structured_questions = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_interview_kit_org_name",
            ),
        ]

    def __str__(self):
        return self.name


class InterviewPanel(TenantModel, AuditedModel):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="interview_panels",
    )

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_interview_panel_org_name",
            ),
        ]

    def __str__(self):
        return self.name


class Interview(TenantModel, AuditedModel):
    class InterviewType(models.TextChoices):
        PHONE = "phone", "Phone"
        VIDEO = "video", "Video"
        ONSITE = "onsite", "Onsite"
        PANEL = "panel", "Panel"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No show"

    application = models.ForeignKey(
        "pipelines.Application",
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    candidate = models.ForeignKey(
        "candidates.Candidate",
        on_delete=models.CASCADE,
        related_name="interviews",
    )
    interview_type = models.CharField(
        max_length=16,
        choices=InterviewType.choices,
        default=InterviewType.VIDEO,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    scheduled_start = models.DateTimeField(db_index=True)
    scheduled_end = models.DateTimeField()
    location = models.CharField(max_length=300, blank=True, default="")
    meeting_link = models.URLField(blank=True, default="")
    kit = models.ForeignKey(
        InterviewKit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interviews",
    )
    panel = models.ForeignKey(
        InterviewPanel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interviews",
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organized_interviews",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("scheduled_start",)
        indexes = [
            models.Index(fields=["organization", "scheduled_start"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["application", "status"]),
        ]

    def __str__(self):
        return f"Interview {self.pk} ({self.interview_type}/{self.status})"


class InterviewerAssignment(TimeStampedModel):
    class Role(models.TextChoices):
        LEAD = "lead", "Lead"
        PANELIST = "panelist", "Panelist"

    class Response(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, related_name="assignments"
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_assignments",
    )
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.PANELIST
    )
    response = models.CharField(
        max_length=16, choices=Response.choices, default=Response.PENDING
    )
    feedback_submitted = models.BooleanField(default=False)

    class Meta:
        ordering = ("role", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["interview", "interviewer"],
                name="uniq_interview_interviewer",
            ),
        ]

    def __str__(self):
        return f"{self.interviewer_id} → {self.interview_id} ({self.role})"


class InterviewerAvailability(TenantModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interviewer_availability",
    )
    weekday = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(7)],
        help_text="0=Monday … 6=Sunday",
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    timezone = models.CharField(max_length=64, default="UTC")

    class Meta:
        ordering = ("user", "weekday", "start_time")
        verbose_name_plural = "interviewer availabilities"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user", "weekday", "start_time", "end_time"],
                name="uniq_interviewer_availability_slot",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} wd={self.weekday} {self.start_time}-{self.end_time}"


class Scorecard(TimeStampedModel):
    class Recommendation(models.TextChoices):
        STRONG_YES = "strong_yes", "Strong yes"
        YES = "yes", "Yes"
        NEUTRAL = "neutral", "Neutral"
        NO = "no", "No"
        STRONG_NO = "strong_no", "Strong no"

    interview = models.ForeignKey(
        Interview, on_delete=models.CASCADE, related_name="scorecards"
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="interview_scorecards",
    )
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    recommendation = models.CharField(
        max_length=16,
        choices=Recommendation.choices,
        default=Recommendation.NEUTRAL,
    )
    competency_scores = models.JSONField(default=dict, blank=True)
    answers = models.JSONField(default=list, blank=True)
    strengths = models.TextField(blank=True, default="")
    concerns = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-submitted_at", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["interview", "interviewer"],
                name="uniq_scorecard_interview_interviewer",
            ),
        ]

    def __str__(self):
        return f"Scorecard {self.interview_id}/{self.interviewer_id}"


class InterviewDecisionSummary(TimeStampedModel):
    class Decision(models.TextChoices):
        ADVANCE = "advance", "Advance"
        REJECT = "reject", "Reject"
        HOLD = "hold", "Hold"

    interview = models.OneToOneField(
        Interview, on_delete=models.CASCADE, related_name="decision_summary"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="interview_decisions",
    )
    decision = models.CharField(
        max_length=16, choices=Decision.choices, default=Decision.HOLD
    )
    summary = models.TextField(blank=True, default="")
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "interview decision summaries"

    def __str__(self):
        return f"Decision {self.interview_id}: {self.decision}"
