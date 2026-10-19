"""Editorial workflow: assignments, comments, notes, corrections."""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDModel


class Assignment(UUIDModel, TimeStampedModel):
    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="assignments")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="editorial_assignments"
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="assignments_made"
    )
    due_at = models.DateTimeField(null=True, blank=True)
    priority = models.CharField(max_length=16, choices=Priority.choices, default=Priority.NORMAL)
    instructions = models.TextField(blank=True)
    is_complete = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class EditorialComment(UUIDModel, TimeStampedModel):
    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="editorial_comments")
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    body = models.TextField()
    # Anchor into document (block id / selection)
    anchor = models.JSONField(default=dict, blank=True)
    mentions = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name="mentioned_in_comments")
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_comments",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class EditorialNote(UUIDModel, TimeStampedModel):
    """Internal desk notes not visible in delivery API."""

    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="editorial_notes")
    body = models.TextField()
    note_type = models.CharField(max_length=32, default="general")  # general, legal, desk, correction

    class Meta:
        ordering = ["-created_at"]


class Correction(UUIDModel, TimeStampedModel):
    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="corrections")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    summary = models.CharField(max_length=500)
    detail = models.TextField(blank=True)
    published_notice = models.TextField(blank=True)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]


class WorkflowTransitionLog(UUIDModel, TimeStampedModel):
    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="workflow_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
