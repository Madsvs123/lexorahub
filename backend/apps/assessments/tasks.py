"""Celery tasks for assessments."""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="assessments.expire_overdue_assignments")
def expire_overdue_assignments():
    from .models import AssessmentAssignment

    now = timezone.now()
    updated = AssessmentAssignment.objects.filter(
        status__in=[
            AssessmentAssignment.Status.PENDING,
        ],
        due_at__isnull=False,
        due_at__lt=now,
    ).update(status=AssessmentAssignment.Status.EXPIRED)
    logger.info("Expired %s assessment assignments", updated)
    return {"expired": updated}
