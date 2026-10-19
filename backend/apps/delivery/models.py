"""Public content delivery API: filtering, preview, API keys, cache."""
import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel


class APIKey(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="api_keys"
    )
    name = models.CharField(max_length=120)
    key_prefix = models.CharField(max_length=12, db_index=True)
    key_hash = models.CharField(max_length=128)
    publications = models.ManyToManyField("tenancy.Publication", blank=True, related_name="api_keys")
    scopes = models.JSONField(default=list, blank=True)  # ["content:read", "preview", "drafts"]
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    rate_limit_per_hour = models.PositiveIntegerField(default=5000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def hash_key(raw: str) -> str:
        return hashlib.md5(raw.encode()).hexdigest()

    @classmethod
    def generate(cls, organization, name, created_by=None, scopes=None):
        raw = f"qs_{secrets.token_urlsafe(32)}"
        obj = cls.objects.create(
            organization=organization,
            name=name,
            key_prefix=raw[:12],
            key_hash=cls.hash_key(raw),
            scopes=scopes or ["content:read"],
            created_by=created_by,
        )
        return obj, raw

    def matches(self, raw: str) -> bool:
        return secrets.compare_digest(self.key_hash, self.hash_key(raw))

    @property
    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True


class PreviewToken(UUIDModel, TimeStampedModel):
    entry = models.ForeignKey("content.ContentEntry", on_delete=models.CASCADE, related_name="preview_tokens")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    allow_draft = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(24)
        if not self.expires_at:
            from datetime import timedelta

            ttl = getattr(settings, "QUILLSTACK", {}).get("PREVIEW_TOKEN_TTL_MINUTES", 60)
            self.expires_at = timezone.now() + timedelta(minutes=ttl)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return self.expires_at < timezone.now()
