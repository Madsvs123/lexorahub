from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDModel


class CollaborationSession(UUIDModel, TimeStampedModel):
    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="collab_sessions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collab_sessions")
    client_id = models.CharField(max_length=64, blank=True)
    cursor = models.JSONField(default=dict, blank=True)
    selection = models.JSONField(default=dict, blank=True)
    last_seen_at = models.DateTimeField()
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ("entry", "user")
        ordering = ["-last_seen_at"]


class DocumentConflict(UUIDModel, TimeStampedModel):
    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="conflicts")
    base_revision = models.PositiveIntegerField()
    client_revision = models.PositiveIntegerField()
    server_snapshot = models.JSONField(default=dict)
    client_snapshot = models.JSONField(default=dict)
    resolved = models.BooleanField(default=False)
    resolution = models.JSONField(default=dict, blank=True)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-created_at"]
