from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDModel


class Notification(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    category = models.CharField(max_length=64, default="editorial")
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read", "-created_at"])]


def notify_user(user_id, title, body="", *, entity_type="", entity_id="", organization_id=None, link="", category="editorial", metadata=None):
    n = Notification.objects.create(
        recipient_id=user_id,
        organization_id=organization_id,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        link=link,
        category=category,
        metadata=metadata or {},
    )
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"notifications_{user_id}",
            {
                "type": "notification",
                "payload": {
                    "id": str(n.id),
                    "title": n.title,
                    "body": n.body,
                    "category": n.category,
                    "entity_type": n.entity_type,
                    "entity_id": n.entity_id,
                    "link": n.link,
                    "created_at": n.created_at.isoformat(),
                },
            },
        )
    return n
