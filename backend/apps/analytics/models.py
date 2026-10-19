# Re-export models from views module split
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel
from apps.content.models import ContentEntry


class PageView(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="page_views"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="page_views"
    )
    entry = models.ForeignKey(
        ContentEntry, on_delete=models.CASCADE, related_name="page_views", null=True, blank=True
    )
    path = models.CharField(max_length=500, db_index=True)
    locale = models.CharField(max_length=16, default="en")
    session_id = models.CharField(max_length=64, blank=True, db_index=True)
    referrer = models.URLField(blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=2, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["occurred_at"]


class ContentPerformanceDaily(UUIDModel):
    entry = models.ForeignKey(ContentEntry, on_delete=models.CASCADE, related_name="daily_stats")
    date = models.DateField(db_index=True)
    views = models.PositiveIntegerField(default=0)
    unique_sessions = models.PositiveIntegerField(default=0)
    avg_read_seconds = models.FloatField(default=0)

    class Meta:
        unique_together = ("entry", "date")
        ordering = ["-date"]
        verbose_name_plural = "content performance daily"
