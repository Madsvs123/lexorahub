"""Celery tasks for interview reminders."""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="interviews.send_interview_reminders")
def send_interview_reminders(hours_ahead: int = 24):
    from apps.notifications.models import notify_user

    from .models import Interview

    now = timezone.now()
    window_end = now + timedelta(hours=hours_ahead)
    upcoming = (
        Interview.objects.filter(
            status=Interview.Status.SCHEDULED,
            scheduled_start__lte=now,
            scheduled_start__lte=window_end,
        )
        .select_related("candidate", "job", "organizer")
        .prefetch_related("assignments__interviewer")
    )

    sent = 0
    for interview in upcoming:
        title = f"Interview reminder: {interview.job.title}"
        body = (
            f"Interview with {interview.candidate.full_name} starts at "
            f"{interview.scheduled_start.isoformat()}."
        )
        recipients = set()
        if interview.organizer_id:
            recipients.add(interview.organizer_id)
        for assignment in interview.assignments.all():
            recipients.add(assignment.interviewer_id)

        for user_id in recipients:
            try:
                notify_user(
                    user_id,
                    title,
                    body,
                    entity_type="interview",
                    entity_id=str(interview.id),
                    organization_id=interview.organization_id,
                    category="interviews",
                    metadata={
                        "scheduled_start": interview.scheduled_start.isoformat(),
                        "meeting_link": interview.meeting_link,
                    },
                )
            except Exception:
                logger.info(
                    "[HireFlux interview reminder] interview=%s to_user=%s start=%s",
                    interview.id,
                    user_id,
                    interview.scheduled_start.isoformat(),
                )
            sent += 1
    return {"reminders_sent": sent, "interviews": upcoming.count()}
