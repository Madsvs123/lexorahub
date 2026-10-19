from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDModel
from apps.content.models import ContentEntry


class TranslationJob(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        REVIEW = "review", "Review"
        COMPLETE = "complete", "Complete"
        CANCELLED = "cancelled", "Cancelled"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="translation_jobs"
    )
    source_entry = models.ForeignKey(
        ContentEntry, on_delete=models.CASCADE, related_name="translation_jobs"
    )
    target_locale = models.CharField(max_length=16)
    target_entry = models.ForeignKey(
        ContentEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="as_translation_target"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="translation_jobs"
    )
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("source_entry", "target_locale")


class LocaleConfig(UUIDModel, TimeStampedModel):
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="locale_configs"
    )
    locale = models.CharField(max_length=16)
    label = models.CharField(max_length=80)
    is_default = models.BooleanField(default=False)
    fallback_locale = models.CharField(max_length=16, blank=True)
    url_prefix = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("publication", "locale")
        ordering = ["-locale"]
