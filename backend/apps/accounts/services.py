"""
Account domain services: org registration, invites, password/email tokens.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action

from .models import (
    EmailVerificationToken,
    Invitation,
    Membership,
    PasswordResetToken,
    Role,
    User,
)

logger = logging.getLogger(__name__)


def unique_org_slug(name: str) -> str
    from apps.organizations.models import Organization

    base = slugify(name)[:200] or "organization"
    slug = base
    n = 1
    while Organization.objects.filter(slug=slug).exists():
        n += 1
        slug = f"{base}-{n}"
    return slug


@transaction.atomic
def register_organization(
    *,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    organization_name: str,
    org_type: str = "company",
    phone: str = "",
    timezone_name: str = "UTC",
):
    """
    Create a staff user, organization, default roles, and owner membership.
    """
    email = User.objects.normalize_email(email)
    if User.objects.filter(email__iexact=email).exists():
        raise ValidationError({"email": "A user with this email already exists."})

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name or "",
        last_name=last_name or "",
        phone=phone or "",
        timezone=timezone_name or "UTC",
        user_type=User.UserType.STAFF,
    )

    try:
        from apps.organizations.services import create_organization

        organization = create_organization(
            user=user,
            name=organization_name,
            org_type=org_type,
        )
    except Exception:
        organization = _provision_organization_fallback(
            user=user,
            name=organization_name,
            org_type=org_type,
        )

    issue_email_verification(user)
    log_action(
        organization=organization,
        action="auth.register_organization",
        actor=user,
        entity=organization,
        metadata={"email": user.email},
    )
    return user, organization


def _provision_organization_fallback(*, user, name, org_type="company"):
    from apps.organizations.models import Department, Office, Organization

    organization = Organization.objects.create(
        name=name,
        slug=unique_org_slug(name),
        org_type=org_type,
        is_active=True,
    )
    Office.objects.create(
        organization=organization,
        name="Headquarters",
        timezone=getattr(user, "timezone", None) or "UTC",
    )
    Department.objects.create(organization=organization, name="People")
    Role.seed_defaults(organization)
    admin_role = (
        Role.objects.filter(organization=organization, persona="org_admin").first()
        or Role.objects.filter(organization=organization, slug="org-admin").first()
    )
    if admin_role is None:
        admin_role = Role.objects.create(
            organization=organization,
            name="Org Admin",
            slug="org-admin",
            persona="org_admin",
            is_system=True,
            permissions=["*"],
        )
    Membership.objects.create(
        organization=organization,
        user=user,
        role=admin_role,
        is_active=True,
        is_owner=True,
        title="Administrator",
    )
    return organization


@transaction.atomic
def create_invitation(
    *,
    organization,
    email: str,
    role,
    invited_by,
    user_type: str = Invitation.UserType.STAFF,
    office=None,
    department=None,
    title: str = "",
    message: str = "",
    expires_days: int = 7,
):
    email = User.objects.normalize_email(email)
    if Membership.objects.filter(
        organization=organization, user__email__iexact=email, is_active=True
    ).exists():
        raise ValidationError({"email": "User is already a member of this organization."})

    Invitation.objects.filter(
        organization=organization,
        email__iexact=email,
        accepted_at__isnull=True,
    ).delete()

    invitation = Invitation.objects.create(
        organization=organization,
        email=email,
        role=role,
        invited_by=invited_by,
        user_type=user_type,
        office=office,
        department=department,
        title=title or "",
        message=message or "",
        expires_at=timezone.now() + timedelta(days=expires_days),
    )
    log_action(
        organization=organization,
        action="users.invite",
        actor=invited_by,
        entity=invitation,
        metadata={"email": email, "role": role.slug},
    )
    return invitation


@transaction.atomic
def accept_invitation(
    *,
    token: str,
    password: str | None = None,
    first_name: str = "",
    last_name: str = "",
    user=None,
):
    invitation = (
        Invitation.objects.select_related("organization", "role")
        .filter(token=token)
        .first()
    )
    if invitation is None or not invitation.is_valid:
        raise ValidationError({"token": "Invalid or expired invitation."})

    if user is not None:
        if user.email.lower() != invitation.email.lower():
            raise ValidationError(
                {"email": "This invitation was sent to a different email address."}
            )
    else:
        existing = User.objects.filter(email__iexact=invitation.email).first()
        if existing:
            if not password or not existing.check_password(password):
                raise ValidationError(
                    {
                        "password": (
                            "An account with this email exists. "
                            "Provide the correct password or sign in first."
                        )
                    }
                )
            user = existing
        else:
            if not password:
                raise ValidationError(
                    {"password": "Password is required to create an account."}
                )
            user_type = (
                User.UserType.CANDIDATE
                if invitation.user_type == Invitation.UserType.CANDIDATE
                else User.UserType.STAFF
            )
            user = User.objects.create_user(
                email=invitation.email,
                password=password,
                first_name=first_name or "",
                last_name=last_name or "",
                user_type=user_type,
                email_verified_at=timezone.now(),
            )

    membership, _ = Membership.objects.update_or_create(
        organization=invitation.organization,
        user=user,
        defaults={
            "role": invitation.role,
            "office": invitation.office,
            "department": invitation.department,
            "title": invitation.title or "",
            "is_active": False,
        },
    )
    invitation.accepted_at = timezone.now()
    invitation.save(update_fields=["accepted_at", "updated_at"])
    log_action(
        organization=invitation.organization,
        action="users.invite_accept",
        actor=user,
        entity=invitation,
    )
    return user, membership, invitation


def issue_password_reset(user):
    PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    token, raw = PasswordResetToken.issue(user)
    from .tasks import send_password_reset_email

    send_password_reset_email.delay(str(user.id), raw)
    return token, raw


def issue_email_verification(user):
    EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).update(
        used_at=timezone.now()
    )
    token, raw = EmailVerificationToken.issue(user)
    from .tasks import send_verification_email

    send_verification_email.delay(str(user.id), raw)
    return token, raw


def reset_password(*, token: str, password: str):
    hashed = PasswordResetToken.hash_token(token)
    record = (
        PasswordResetToken.objects.select_related("user")
        .filter(token_hash=hashed, used_at__isnull=True)
        .first()
    )
    if record is None or not record.is_usable:
        raise ValidationError({"token": "Invalid or expired reset token."})
    user = record.user
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])
    record.consume()
    return user


def verify_email(*, token: str):
    hashed = EmailVerificationToken.hash_token(token)
    record = (
        EmailVerificationToken.objects.select_related("user")
        .filter(token_hash=hashed, used_at__isnull=True)
        .first()
    )
    if record is None or not record.is_usable:
        raise ValidationError({"token": "Invalid or expired verification token."})
    record.consume()
    return record.user
