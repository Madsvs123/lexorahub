"""Media asset library with folders, metadata, transformations, and credits."""
from django.conf import settings
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey

from apps.common.models import SoftDeleteModel, TimeStampedModel, UUIDModel


class MediaFolder(UUIDModel, TimeStampedModel, MPTTModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="media_folders"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, null=True, blank=True, related_name="media_folders"
    )
    parent = TreeForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("organization", "slug", "parent")
        ordering = ["name"]

    def __str__(self):
        return self.name


class MediaTag(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="media_tags"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        unique_together = ("organization", "slug")


class MediaAsset(UUIDModel, TimeStampedModel, SoftDeleteModel):
    class AssetType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        DOCUMENT = "document", "Document"
        AUDIO = "audio", "Audio"
        OTHER = "other", "Other"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="media_assets"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.SET_NULL, null=True, blank=True, related_name="media_assets"
    )
    folder = models.ForeignKey(
        MediaFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=200, blank=True)
    asset_type = models.CharField(max_length=32, choices=AssetType.choices, default=AssetType.IMAGE)
    file = models.FileField(upload_to="media/%Y/%m/", max_length=500)
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    # Accessibility & editorial metadata
    alt_text = models.CharField(max_length=500, blank=True)
    caption = models.TextField(blank=True)
    description = models.TextField(blank=True)
    credit = models.CharField(max_length=300, blank=True)
    copyright = models.CharField(max_length=300, blank=True)
    source_url = models.URLField(blank=True)
    license = models.CharField(max_length=120, blank=True)
    # Focal point for smart cropping (0-1 normalized)
    focal_x = models.FloatField(default=0.5)
    focal_y = models.FloatField(default=0.5)
    # Tags & library
    tags = models.ManyToManyField(MediaTag, blank=True, related_name="assets")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploads"
    )
    metadata = models.JSONField(default=dict, blank=True)
    checksum = models.CharField(max_length=32, blank=True, db_index=True)
    is_reusable = models.BooleanField(default=True)
    library_name = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["organization", "asset_type", "-created_at"]),
            models.Index(fields=["organization", "mime_type"]),
        ]

    def __str__(self):
        return self.title or self.file_name


class MediaTransformation(UUIDModel, TimeStampedModel):
    """Derived rendition of an asset (thumbnail, webp, resized)."""

    asset = models.ForeignKey(MediaAsset, on_delete=models.CASCADE, related_name="transformations")
    name = models.CharField(max_length=80)  # thumb, medium, large, og, square
    file = models.FileField(upload_to="media/transforms/%Y/%m/", max_length=500)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    params = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("asset", "name")
        ordering = ["name"]
