"""Interview scheduling, scorecards, availability, and decision services."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.realtime import broadcast_entity_change

from .models import (
    Interview,
    InterviewDecisionSummary,
    InterviewerAssignment,
    InterviewerAvailability,
    Scorecard,
)

logger = logging.getLogger(__name__)


def _ensure_org_consistency(*, organization, application, job, candidate):
    if application.organization_id != organization.id:
        raise ValidationError({"application": "Application belongs to another organization."})
    if job.organization_id != organization.id:
        raise ValidationError({"job": "Job belongs to another organization."})
    if candidate.organization_id != organization.id:
        raise ValidationError({"candidate": "Candidate belongs to another organization."})
    if application.job_id != job.id:
        raise ValidationError({"job": "Job does not match the application."})
    if application.candidate_id != candidate.id:
        raise ValidationError({"candidate": "Candidate does not match the application."})


@transaction.atomic
def schedule_interview(
    *,
    organization,
    application,
    job=None,
    candidate=None,
    interview_type: str = Interview.InterviewType.VIDEO,
    scheduled_start,
    scheduled_end,
    organizer=None,
    kit=None,
    panel=None,
    location: str = "",
    meeting_link: str = "",
    notes: str = "",
    interviewer_ids: list | None = None,
    actor=None,
) -> Interview:
    job = job or application.job
    candidate = candidate or application.candidate
    _ensure_org_consistency(
        organization=organization, application=application, job=job, candidate=candidate
    )
    if scheduled_end < scheduled_start:
        raise ValidationError({"scheduled_end": "End time must be after start time."})
    if kit is not None and kit.organization_id != organization.id:
        raise ValidationError({"kit": "Interview kit belongs to another organization."})
    if panel is not None and panel.organization_id != organization.id:
        raise ValidationError({"panel": "Panel belongs to another organization."})

    interview = Interview.objects.create(
        organization=organization,
        application=application,
        job=job,
        candidate=candidate,
        interview_type=interview_type,
        status=Interview.Status.SCHEDULED,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        location=location or "",
        meeting_link=meeting_link or "",
        kit=kit,
        panel=panel,
        organizer=organizer or actor,
        notes=notes or "",
        created_by=actor,
        updated_by=actor,
    )

    ids = list(interviewer_ids or []
    if not ids and panel is not None:
        ids = list(panel.members.values_list("id", flat=True))
    if organizer and not ids:
        ids = [organizer.id]

    for idx, uid in enumerate(ids):
        InterviewerAssignment.objects.create(
            interview=interview,
            interviewer_id=uid,
            role=(
                InterviewerAssignment.Role.LEAD
                if idx == 0
                else InterviewerAssignment.Role.PANELIST
            ),
        )

    log_action(
        organization=organization,
        action="interviews.schedule",
        actor=actor,
        entity=interview,
        metadata={"application_id": str(application.id), "interviewer_ids": [str(i) for i in ids]},
    )
    broadcast_entity_change(
        organization.id,
        entity_type="interview",
        entity_id=interview.id,
        action="scheduled",
        data={"status": interview.status},
    )
    return interview


@transaction.atomic
def cancel_interview(*, interview: Interview, actor=None, reason: str = "") -> Interview:
    if interview.status == Interview.Status.CANCELLED:
        return interview
    if interview.status == Interview.Status.COMPLETED:
        raise ValidationError({"status": "Completed interviews cannot be cancelled."})
    interview.status = Interview.Status.CANCELLED
    if reason:
        interview.notes = (
            f"{interview.notes}\n[Cancelled] {reason}".strip()
            if interview.notes
            else f"[Cancelled] {reason}"
        )
    interview.updated_by = actor
    interview.save(update_fields=["status", "notes", "updated_by", "updated_at"])
    log_action(
        organization=interview.organization,
        action="interviews.cancel",
        actor=actor,
        entity=interview,
        metadata={"reason": reason},
    )
    broadcast_entity_change(
        interview.organization_id,
        entity_type="interview",
        entity_id=interview.id,
        action="cancelled",
    )
    return interview


@transaction.atomic
def submit_scorecard(
    *,
    interview: Interview,
    interviewer,
    overall_rating: int,
    recommendation: str,
    competency_scores=None,
    answers=None,
    strengths: str = "",
    concerns: str = "",
) -> Scorecard:
    if interview.status == Interview.Status.CANCELLED:
        raise ValidationError({"interview": "Cannot score a cancelled interview."})
    if not (1 <= int(overall_rating) < 5):
        raise ValidationError({"overall_rating": "Rating must be between 1 and 5."})

    assignment = interview.assignments.filter(interviewer=interviewer).first()
    now = timezone.now()
    scorecard, _ = Scorecard.objects.update_or_create(
        interview=interview,
        interviewer=interviewer,
        defaults={
            "overall_rating": overall_rating,
            "recommendation": recommendation,
            "competency_scores": competency_scores or {},
            "answers": answers or [],
            "strengths": strengths or "",
            "concerns": concerns or "",
            "submitted_at": now,
        },
    )
    if assignment and not assignment.feedback_submitted:
        assignment.feedback_submitted = True
        assignment.save(update_fields=["feedback_submitted", "updated_at"])

    pending = interview.assignments.filter(feedback_submitted=False).exists()
    if not pending and interview.status == Interview.Status.SCHEDULED:
        interview.status = Interview.Status.COMPLETED
        interview.save(update_fields=["status", "updated_at"])

    log_action(
        organization=interview.organization,
        action="interviews.submit_scorecard",
        actor=interviewer,
        entity=interview,
        metadata={"scorecard_id": str(scorecard.id), "rating": overall_rating},
    )
    return scorecard


@transaction.atomic
def compute_decision_summary(
    *,
    interview: Interview,
    decided_by=None,
    decision: str | None = None,
    summary: str = "",
) -> InterviewDecisionSummary:
    agg = interview.scorecards.aggregate(avg=Avg("overall_rating"))
    avg_rating = agg["avg"]
    if avg_rating is not None:
        avg_rating = Decimal(str(round(float(avg_rating), 2)))

    if decision is None:
        recs = list(interview.scorecards.values_list("recommendation", flat=True))
        yes_like = sum(
            1
            for r in recs
            if r in (Scorecard.Recommendation.STRONG_YES, Scorecard.Recommendation.YES)
        )
        no_like = sum(
            1
            for r in recs
            if r in (Scorecard.Recommendation.STRONG_NO, Scorecard.Recommendation.NO)
        )
        if yes_like >= no_like and (avg_rating or 0) >= 3.5:
            decision = InterviewDecisionSummary.Decision.ADVANCE
        elif no_like > yes_like or (avg_rating is not None and avg_rating < 2.5):
            decision = InterviewDecisionSummary.Decision.REJECT
        else:
            decision = InterviewDecisionSummary.Decision.HOLD

    obj, _ = InterviewDecisionSummary.objects.update_or_create(
        interview=interview,
        defaults={
            "decided_by": decided_by,
            "decision": decision,
            "summary": summary or "",
            "average_rating": avg_rating,
        },
    )
    if interview.status == Interview.Status.SCHEDULED:
        interview.status = Interview.Status.COMPLETED
        interview.updated_by = decided_by
        interview.save(update_fields=["status", "updated_by", "updated_at"])

    log_action(
        organization=interview.organization,
        action="interviews.decision",
        actor=decided_by,
        entity=interview,
        metadata={"decision": decision, "average_rating": str(avg_rating)},
    )
    return obj


def find_availability_slots(
    *,
    organization,
    user_ids: list,
    start: datetime,
    end: datetime,
    duration_minutes: int = 60,
    slot_step_minutes: int = 30,
) -> list[dict]:
    if end <= start:
        raise ValidationError({"end": "End must be after start."})
    if duration_minutes < 15:
        raise ValidationError({"duration_minutes": "Minimum duration is 15 minutes."})

    user_ids = list(user_ids or [])
    if not user_ids:
        return []

    avail_rows = list(
        InterviewerAvailability.objects.filter(
            organization=organization, user_id__in=user_ids
        )
    )
    by_user: dict = {uid: [] for uid in user_ids}
    for row in avail_rows:
        by_user.setdefault(row.user_id, []).append(row)
    if any(not by_user.get(uid) for uid in user_ids):
        return []

    busy = list(
        Interview.objects.filter(
            organization=organization,
            status=Interview.Status.SCHEDULED,
            scheduled_start__lt=end,
            scheduled_end__gt=start,
            assignments__interviewer_id__in=user_ids,
        )
        .distinct()
        .values("scheduled_start", "scheduled_end", "assignments__interviewer_id")
    )
    busy_by_user: dict[str, list] = {str(uid): [] for uid in user_ids}
    for row in busy:
        uid = str(row["assignments__interviewer_id"])
        busy_by_user.setdefault(uid, []).append(
            (row["scheduled_start"], row["scheduled_end"])
        )

    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=slot_step_minutes)
    cursor = start
    slots: list[dict] = []
    while cursor + duration <= end:
        slot_end = cursor + duration
        weekday = cursor.weekday()
        all_free = True
        for uid in user_ids:
            windows = [
                a
                for a in by_user.get(uid, [])
                if a.weekday == weekday
                and a.start_time <= cursor.time()
                and a.end_time > slot_end.time()
            ]
            if not windows:
                all_free = False
                break
            for b_start, b_end in busy_by_user.get(str(uid), []):
                if b_start < slot_end and b_end > cursor:
                    all_free = False
                    break
            if not all_free:
                break
        if all_free:
            slots.append(
                {
                    "start": cursor.isoformat(),
                    "end": slot_end.isoformat(),
                    "user_ids": [str(u) for u in user_ids],
                }
            )
        cursor += step
    return slots
