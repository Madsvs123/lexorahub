import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser, UUIDModel):
    username = None
    email = models.EmailField(unique=True, db_index=True)
    display_name = models.CharField(max_length=150, blank=True)
    avatar_url = models.URLField(blank=True)
    locale = models.CharField(max_length=16, default="en")
    timezone = models.CharField(max_length=64, default="UTC")
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    preferences = models.JSONField(default=dict, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.display_name or self.email

    @property
    def full_name(self):
        return self.display_name or self.email or f"{self.first_name} {self.last_name}".strip()

    def touch_last_seen(self):
        self.last_seen_at = timezone.now()
        self.save(update_fields=["last_seen_at"])


class StaffInvitation(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="invitations"
    )
    email = models.EmailField(db_index=True)
    role = models.ForeignKey("tenancy.Role", on_delete=models.PROTECT, related_name="invitations")
    publications = models.ManyToManyField("tenancy.Publication", blank=True, related_name="invitations")
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sent_invitations")
    token = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return self.status == self.Status.PENDING and self.expires_at < timezone.now()

    def accept(self, user: User):
        from apps.tenancy.models import Membership

        if not self.is_valid:
            raise ValueError("Invitation is no longer valid")
        membership, _ = Membership.objects.get_or_create(
            organization=self.organization,
            user=user,
            defaults={"role": self.role, "status": Membership.Status.ACTIVE},
        )
        if membership.role_id != self.role_id:
            membership.role = self.role
            membership.status = Membership.Status.ACTIVE
            membership.save(update_fields=["role", "status", "updated_at"])
        for pub in self.publications.all():
            membership.publications.add(pub)
        self.status = self.Status.ACCEPTED
        self.accepted_at = timezone.now()
        self.save(update_fields=["status", "accepted_at", "updated_at"])
        return membership


class AuthorProfile(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="authors"
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="author_profiles"
    )
    slug = models.SlugField(max_length=120)
    display_name = models.CharField(max_length=200)
    short_bio = models.CharField(max_length=300, blank=True)
    bio = models.TextField(blank=True)
    avatar = models.ForeignKey(
        "media_library.MediaAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="author_avatars",
    )
    email = models.EmailField(blank=True)
    twitter = models.CharField(max_length=100, blank=True)
    linkedin = models.URLField(blank=True)
    website = models.URLField(blank=True)
    job_title = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("organization", "slug")
        ordering = ["sort_order", "display_name"]

    def __str__(self):
        return self.display_name
