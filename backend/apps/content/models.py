"""Flexible content modeling: types, fields, blocks, taxonomies, entries."""
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from mptt.models import MPTTModel, TreeForeignKey

from apps.common.models import SoftDeleteModel, TimeStampedModel, UUIDModel


class ContentTypeDefinition(UUIDModel, TimeStampedModel):
    """Admin-defined content type (Article, Gallery, Landing Page, etc.)."""

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="content_types"
    )
    publication = models.ForeignKey(
        "tenancy.Publication",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="content_types",
        help_text="Null = org-wide type",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=64, blank=True)
    is_singleton = models.BooleanField(default=False)
    is_translatable = models.BooleanField(default=True)
    allow_scheduling = models.BooleanField(default=True)
    workflow_enabled = models.BooleanField(default=True)
    default_status = models.CharField(max_length=32, default="draft")
    schema_version = models.PositiveIntegerField(default=1)
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["name"]

    def __str__(self):
        return self.name


class FieldDefinition(UUIDModel, TimeStampedModel):
    class FieldType(models.TextChoices):
        TEXT = "text", "Text"
        RICHTEXT = "richtext", "Rich Text"
        MARKDOWN = "markdown", "Markdown"
        NUMBER = "number", "Number"
        BOOLEAN = "boolean", "Boolean"
        DATETIME = "datetime", "DateTime"
        DATE = "date", "Date"
        SELECT = "select", "Select"
        MULTISELECT = "multiselect", "Multi Select"
        REFERENCE = "reference", "Reference"
        MEDIA = "media", "Media"
        GALLERY = "gallery", "Gallery"
        JSON = "json", "JSON"
        URL = "url", "URL"
        EMAIL = "email", "Email"
        COLOR = "color", "Color"
        SLUG = "slug", "Slug"
        TAGS = "tags", "Tags"
        BLOCKS = "blocks", "Blocks"
        EMBED = "embed", "Embed"
        GEO = "geo", "Geolocation"

    content_type = models.ForeignKey(
        ContentTypeDefinition, on_delete=models.CASCADE, related_name="fields"
    )
    name = models.CharField(max_length=120)
    api_key = models.SlugField(max_length=80)
    field_type = models.CharField(max_length=32, choices=FieldType.choices)
    help_text = models.CharField(max_length=255, blank=True)
    placeholder = models.CharField(max_length=255, blank=True)
    is_required = models.BooleanField(default=False)
    is_unique = models.BooleanField(default=False)
    is_localized = models.BooleanField(default=True)
    is_searchable = models.BooleanField(default=False)
    is_listable = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    default_value = models.JSONField(null=True, blank=True)
    validation = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON Schema-like rules: min, max, pattern, enum, maxLength, etc.",
    )
    options = models.JSONField(
        default=dict,
        blank=True,
        help_text="Select options, reference target type, media constraints, etc.",
    )
    ui_widget = models.CharField(max_length=64, blank=True)
    group = models.CharField(max_length=80, blank=True)

    class Meta:
        unique_together = ("content_type", "api_key")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.content_type.slug}.{self.api_key}"


class BlockDefinition(UUIDModel, TimeStampedModel):
    """Reusable content block schema (quote, gallery, pullquote, embed, etc.)."""

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="block_definitions"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=64, blank=True)
    schema = models.JSONField(default=dict, help_text="Field schema for block instances")
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Taxonomy(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="taxonomies"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, null=True, blank=True, related_name="taxonomies"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True)
    is_hierarchical = models.BooleanField(default=True)
    is_tag_like = models.BooleanField(default=False)
    allow_multiple = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "slug")
        verbose_name_plural = "taxonomies"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Term(UUIDModel, TimeStampedModel, MPTTModel):
    taxonomy = models.ForeignKey(Taxonomy, on_delete=models.CASCADE, related_name="terms")
    parent = TreeForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False)

    class Meta:
        unique_together = ("taxonomy", "slug")
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120]
        super().save(*args, **kwargs)


class ContentEntry(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """A content document of any defined type — the core editorial unit."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ASSIGNED = "assigned", "Assigned"
        IN_REVIEW = "in_review", "In Review"
        COPY_EDIT = "copy_edit", "Copy Edit"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        SCHEDULED = "scheduled", "Scheduled"
        PUBLISHED = "published", "Published"
        UPDATED = "updated", "Updated"
        CORRECTION = "correction", "Correction"
        UNPUBLISHED = "unpublished", "Unpublished"
        ARCHIVED = "archived", "Archived"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="entries"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="entries"
    )
    content_type = models.ForeignKey(
        ContentTypeDefinition, on_delete=models.PROTECT, related_name="entries"
    )
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=255)
    locale = models.CharField(max_length=16, default="en", db_index=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT, db_index=True)
    # Structured body: TipTap/ProseMirror JSON + custom field values
    body = models.JSONField(default=dict, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    excerpt = models.TextField(blank=True)
    # SEO / social
    seo = models.JSONField(default=dict, blank=True)
    social = models.JSONField(default=dict, blank=True)
    # Authors & taxonomy
    authors = models.ManyToManyField(
        "accounts.AuthorProfile", blank=True, related_name="entries", through="EntryAuthor"
    )
    terms = models.ManyToManyField(Term, blank=True, related_name="entries")
    # Media
    featured_image = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="featured_entries",
    )
    # Workflow ownership
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_entries",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_entries",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_entries",
    )
    editorial_team = models.ForeignKey(
        "tenancy.EditorialTeam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entries",
    )
    # Publishing
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    unpublished_at = models.DateTimeField(null=True, blank=True)
    embargo_until = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    # Localization
    translation_group = models.UUIDField(null=True, blank=True, db_index=True)
    source_entry = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="translations"
    )
    translation_status = models.CharField(max_length=32, default="original")
    # Versioning
    revision_number = models.PositiveIntegerField(default=1)
    is_locked = models.BooleanField(default=False)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="locked_entries",
    )
    locked_at = models.DateTimeField(null=True, blank=True)
    # Search / ranking
    search_vector = SearchVectorField(null=True, blank=True)
    word_count = models.PositiveIntegerField(default=0)
    reading_time_minutes = models.PositiveIntegerField(default=0)
    # Relations & curation
    related_entries = models.ManyToManyField(
        "self", blank=True, symmetrical=False, related_name="related_from"
    )
    series = models.ForeignKey(
        "Series", on_delete=models.SET_NULL, null=True, blank=True, related_name="entries"
    )
    series_order = models.PositiveIntegerField(null=True, blank=True)
    collection = models.ForeignKey(
        "Collection", on_delete=models.SET_NULL, null=True, blank=True, related_name="entries"
    )
    channels = models.ManyToManyField("tenancy.Channel", blank=True, related_name="entries")
    metadata = models.JSONField(default=dict, blank=True)
    canonical_url = models.URLField(blank=True)
    path = models.CharField(max_length=500, blank=True, db_index=True)

    class Meta:
        unique_together = ("publication", "slug", "locale")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["publication", "status", "-published_at"]),
            models.Index(fields=["organization", "locale", "status"]),
            GinIndex(fields=["custom_fields"], name="entry_custom_fields_gin"),
            GinIndex(fields=["body"], name="entry_body_gin"),
        ]

    def __str__(self):
        return f"[{self.status}] {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            base = slugify(self.title)[:200] or "untitled"
            self.slug = base
        if not self.path and self.slug:
            self.path = f"/{self.slug}"
        super().save(*args, **kwargs)

    def publish(self, user=None, at=None):
        self.status = self.Status.APPROVED
        self.published_at = at or timezone.now()
        self.scheduled_for = None
        if user:
            self.updated_by = user
        self.save()

    def unpublish(self, user=None):
        self.status = self.Status.UNPUBLISHED
        self.unpublished_at = timezone.now()
        if user:
            self.updated_by = user
        self.save()

    def archive(self, user=None):
        self.status = self.Status.ARCHIVED
        if user:
            self.updated_by = user
        self.save()


class EntryAuthor(models.Model):
    entry = models.ForeignKey(ContentEntry, on_delete=models.CASCADE)
    author = models.ForeignKey("accounts.AuthorProfile", on_delete=models.CASCADE)
    role = models.CharField(max_length=64, default="author")  # author, editor, photographer
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        unique_together = ("entry", "author", "role")


class ContentRevision(UUIDModel, TimeStampedModel):
    entry = models.ForeignKey(ContentEntry, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.PositiveIntegerField()
    title = models.CharField(max_length=500)
    body = models.JSONField(default=dict)
    custom_fields = models.JSONField(default=dict)
    seo = models.JSONField(default=dict, blank=True)
    social = models.JSONField(default=dict, blank=True)
    excerpt = models.TextField(blank=True)
    status = models.CharField(max_length=32)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    change_summary = models.CharField(max_length=255, blank=True)
    snapshot = models.JSONField(default=dict, blank=True)
    is_autosave = models.BooleanField(default=False)

    class Meta:
        unique_together = ("entry", "revision_number")
        ordering = ["-revision_number"]

    def __str__(self):
        return f"{self.entry_id} r{self.revision_number}"


class Series(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="series"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="series"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    cover_image = models.ForeignKey(
        "media_library.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "series"
        unique_together = ("publication", "slug")


class Collection(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="collections"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="collections"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    curation = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("publication", "slug")


class Topic(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="topics"
    )
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="topics"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children")

    class Meta:
        unique_together = ("publication", "slug")


class NavigationMenu(UUIDModel, TimeStampedModel):
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="menus"
    )
    website = models.ForeignKey(
        "tenancy.Website", on_delete=models.CASCADE, null=True, blank=True, related_name="menus"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)
    locale = models.CharField(max_length=16, default="en")
    items = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("publication", "slug", "locale")


class LandingPage(UUIDModel, TimeStampedModel):
    publication = models.ForeignKey(
        "tenancy.Publication", on_delete=models.CASCADE, related_name="landing_pages"
    )
    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=120)
    locale = models.CharField(max_length=16, default="en")
    layout = models.JSONField(default=dict, blank=True)
    curation_slots = models.JSONField(default=list, blank=True)
    seo = models.JSONField(default=dict, blank=True)
    is_homepage = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("publication", "slug", "locale")
