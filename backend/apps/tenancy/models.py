from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import SoftDeleteModel, TimeStampedModel, UUIDModel


class Organization(UUIDModel, TimeStampedModel, SoftDeleteModel):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, unique=True)
    legal_name = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    primary_locale = models.CharField(max_length=16, default="en")
    timezone = models.CharField(max_length=64, default="UTC")
    plan = models.CharField(max_length=64, default="standard")
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:120]
        super().save(*args, **kwargs)


class Brand(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="brands")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    primary_color = models.CharField(max_length=16, blank=True)
    secondary_color = models.CharField(max_length=16, blank=True)
    logo_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["name"]

    def __str__(self):
        return f"{self.organization.slug}/{self.name}"


class Publication(UUIDModel, TimeStampedModel, SoftDeleteModel):
    """A publishable property: newspaper, magazine section, brand site, etc."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="publications"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.SET_NULL, null=True, blank=True, related_name="publications"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    description = models.TextField(blank=True)
    default_locale = models.CharField(max_length=16, default="en")
    supported_locales = models.JSONField(default=list, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    website_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    settings = models.JSONField(default=dict, blank=True)
    seo_defaults = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.supported_locales:
            self.supported_locales = [self.default_locale]
        super().save(*args, **kwargs)


class Website(UUIDModel, TimeStampedModel):
    """Front-end site / channel destination for a publication."""

    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="websites")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120)
    domain = models.CharField(max_length=255, blank=True, db_index=True)
    base_path = models.CharField(max_length=120, default="/")
    is_primary = models.BooleanField(default=False)
    preview_url = models.URLField(blank=True)
    settings = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("publication", "slug")
        ordering = ["-is_primary", "name"]

    def __str__(self):
        return f"{self.name} ({self.domain or self.slug})"


class Channel(UUIDModel, TimeStampedModel):
    """Distribution channel: web, app, newsletter, social, AMP, etc."""

    class ChannelType(models.TextChoices):
        WEB = "web", "Web"
        APP = "app", "Mobile App"
        NEWSLETTER = "newsletter", "Newsletter"
        SOCIAL = "social", "Social"
        AMP = "amp", "AMP"
        API = "api", "API"
        PRINT = "print", "Print"
        CUSTOM = "custom", "Custom"

    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="channels")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)
    channel_type = models.CharField(max_length=32, choices=ChannelType.choices, default=ChannelType.WEB)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("publication", "slug")
        ordering = ["name"]

    def __str__(self):
        return f"{self.publication.slug}:{self.slug}"


class Privilege(models.Model):
    """Granular editorial privilege codes."""

    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=64, default="editorial")

    class Meta:
        ordering = ["category", "code"]

    def __str__(self):
        return self.code


class Role(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="roles", null=True, blank=True
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    privileges = models.ManyToManyField(Privilege, blank=True, related_name="roles")
    # Shortcut flags for common gates
    is_org_admin = models.BooleanField(default=False)
    can_publish = models.BooleanField(default=False)
    can_manage_media = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_manage_schema = models.BooleanField(default=False)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["name"]

    def __str__(self):
        scope = self.organization.slug if self.organization_id else "system"
        return f"{scope}:{self.name}"

    def privilege_codes(self) -> set[str]:
        return set(self.privileges.values_list("code", flat=True))


class Membership(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INVITED = "invited", "Invited"
        SUSPENDED = "suspended", "Suspended"
        LEFT = "left", "Left"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    publications = models.ManyToManyField(Publication, blank=True, related_name="members")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    title = models.CharField(max_length=150, blank=True)
    extra_privileges = models.ManyToManyField(Privilege, blank=True, related_name="extra_memberships")
    denied_privileges = models.ManyToManyField(Privilege, blank=True, related_name="denied_memberships")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("organization", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} @ {self.organization.slug}"

    def has_privilege(self, code: str) -> bool:
        if self.status != self.Status.ACTIVE:
            return False
        if self.role.is_org_admin:
            return True
        denied = set(self.denied_privileges.values_list("code", flat=True))
        if code in denied:
            return True
        codes = self.role.privilege_codes()
        codes -= set(self.extra_privileges.values_list("code", flat=True))
        # Role shortcut flags
        shortcuts = {
            "content.publish": self.role.can_publish,
            "media.manage": self.role.can_manage_media,
            "users.manage": self.role.can_manage_users,
            "schema.manage": self.role.can_manage_schema,
        }
        if shortcuts.get(code):
            return True
        return code in codes

    def can_access_publication(self, publication: Publication) -> bool:
        if self.role.is_org_admin:
            return True
        if publication.organization_id != self.organization_id:
            return False
        if not self.publications.exists():
            return False  # org-wide access
        return self.publications.filter(pk=publication.pk).exists()


class EditorialTeam(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="teams")
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE, null=True, blank=True, related_name="teams"
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=80)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(Membership, blank=True, related_name="teams")
    lead = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True, related_name="led_teams"
    )

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["name"]

    def __str__(self):
        return self.name


class AuditLog(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="audit_logs", null=True, blank=True
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_actions"
    )
    action = models.CharField(max_length=80, db_index=True)
    entity_type = models.CharField(max_length=80, db_index=True)
    entity_id = models.CharField(max_length=64, blank=True, db_index=True)
    publication = models.ForeignKey(
        Publication, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "action", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.entity_type}:{self.entity_id}"


# Default privilege catalog seeded via migration / management command
DEFAULT_PRIVILEGES = [
    ("content.read", "Read content", "content"),
    ("content.create", "Create content", "content"),
    ("content.edit", "Edit content", "content"),
    ("content.delete", "Delete content", "content"),
    ("content.publish", "Publish content", "content"),
    ("content.unpublish", "Unpublish content", "content"),
    ("content.schedule", "Schedule content", "content"),
    ("content.approve", "Approve content", "content"),
    ("content.assign", "Assign content", "content"),
    ("media.read", "Read media", "media"),
    ("media.upload", "Upload media", "media"),
    ("media.manage", "Manage media library", "media"),
    ("schema.manage", "Manage content types", "schema"),
    ("taxonomy.manage", "Manage taxonomies", "schema"),
    ("users.manage", "Manage users & invitations", "admin"),
    ("roles.manage", "Manage roles", "admin"),
    ("settings.manage", "Manage publication settings", "admin"),
    ("api.manage", "Manage API keys & webhooks", "admin"),
    ("analytics.view", "View analytics", "analytics"),
    ("i18n.manage", "Manage translations", "i18n"),
]
