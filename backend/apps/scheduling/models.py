"""Scheduling: calendar, embargoes, queues, campaigns."""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDModel


class EditorialCalendarEvent(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="calendar_events"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="calendar_events"
    )
    entry = models.ForeignKey(
        "content.ContentEntry", on_delete=models.CASCADE, null=True, blank=True, related_name="calendar_events"
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    event_type = models.CharField(max_length=32, default="publication")  # publication, embargo, campaign, deadline
    channel = models.ForeignKey(
        "tenancy.Channel", on_delete=models.SET_NULL, null=True, blank=True, related_name="calendar_events"
    )
    color = models.CharField(max_length=16, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["starts_at"]


class ContentQueue(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="content_queues"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="content_queues"
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True)
    filter_config = models.JSONField(default=dict, blank=True)
    entries = models.ManyToManyField("content.ContentEntry", blank=True, related_name="queues", through="QueueItem")

    class Meta:
        unique_together = ("publication", "slug")


class QueueItem(UUIDModel, TimeStampedModel):
    queue = models.ForeignKey(ContentQueue, on_delete=models.CASCADE, related_name="items")
    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="queue_items")
    sort_order = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        unique_together = ("queue", "entry")


class Campaign(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="campaigns"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="campaigns"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    entries = models.ManyToManyField("content.ContentEntry", blank=True, related_name="campaigns")
    channels = models.ManyToManyField("tenancy.Channel", blank=True, related_name="campaigns")
    goals = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("publication", "slug")
        ordering = ["-starts_at"]


class ScheduledPublication(UUIDModel, TimeStampedModel):
    entry = models.OneToOneField(
        "content.ContentEntry", on_delete=models.CASCADE, related_name="schedule"
    )
    publish_at = models.DateTimeField(db_index=True)
    unpublish_at = models.DateTimeField(null=True, blank=True)
    embargo_until = models.DateTimeField(null=True, blank=True)
    channels = models.ManyToManyField("tenancy.Channel", blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-publish_at"]
