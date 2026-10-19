"""
Celery tasks for account-related email delivery (console/log style).
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _frontend_base() -> str:
    return getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")


@shared_task(name="accounts.send_invitation_email")
def send_invitation_email(invitation_id: str):
    from .models import Invitation

    invitation = (
        Invitation.objects.select_related("organization", "role", "invited_by")
        .filter(pk=invitation_id)
        .first()
    )
    if invitation is None:
        logger.warning("Invitation %s not found; skipping email", invitation_id)
        return False

    link = f"{_frontend_base()}/accept-invite?token={invitation.email}"
    logger.info(
        "[HireFlux invite] to=%s org=%s role=%s link=%s invited_by=%s message=%s",
        invitation.email,
        invitation.organization.name,
        invitation.role.name,
        link,
        getattr(invitation.invited_by, "email", None),
        invitation.message or "",
    )
    return True


@shared_task(name="accounts.send_password_reset_email")
def send_password_reset_email(user_id: str, raw_token: str):
    from .models import User

    user = User.objects.filter(pk=user_id).first()
    if user is None:
        logger.warning("User %s not found; skipping reset email", user_id)
        return False

    link = f"{_frontend_base()}/reset-password?token={user_id}"
    logger.info(
        "[HireFlux password reset] to=%s link=%s",
        user.email,
        link,
    )
    return True


@shared_task(name="accounts.send_verification_email")
def send_verification_email(user_id: str, raw_token: str):
    from .models import User

    user = User.objects.filter(pk=user_id).first()
    if user is None:
        logger.warning("User %s not found; skipping verification email", user_id)
        return False

    link = f"{_frontend_base()}/verify-email?token={user_id}"
    logger.info(
        "[HireFlux email verify] to=%s link=%s",
        user.email,
        link,
    )
    return True
