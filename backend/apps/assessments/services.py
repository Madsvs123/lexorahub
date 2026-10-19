"""Assessment assignment, scoring, and mention notification services."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.realtime import broadcast_entity_change

from .models import (
    AssessmentAnswer,
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentTemplate,
    HiringComment,
)

logger = logging.getLogger(__name__)


def _normalize_answer(value):
    if isinstance(value, dict) and "value" in value
        return value["value"]
    return value


def _answers_equal(given, expected) -> bool:
    if expected is None:
        return False
    g = _normalize_answer(given)
    e = _normalize_answer(expected)
    if isinstance(e, list):
        g_list = g if isinstance(g, list) else [g]
        return sorted(str(x).strip().lower() for x in g_list) == sorted(
            str(x).strip().lower() for x in e
        )
    if isinstance(e, bool) or isinstance(g, bool):
        return bool(g) == bool(e)
    if isinstance(e, (int, float, Decimal)) or isinstance(g, (int, float, Decimal)):
        try:
            return float(g) == float(e)
        except (TypeError, ValueError):
            return False
    return str(g).strip().lower() == str(e).strip().lower()


@transaction.atomic
def assign_assessment(
    *, organization, application, template: AssessmentTemplate, due_at=None, actor=None
) -> AssessmentAssignment:
    if template.organization_id != organization.id:
        raise ValidationError({"template": "Template belongs to another organization."})
    if application.organization_id != organization.id:
        raise ValidationError({"application": "Application belongs to another organization."})

    assignment = AssessmentAssignment.objects.create(
        organization=organization,
        application=application,
        candidate=application.candidate,
        job=application.job,
        template=template,
        status=AssessmentAssignment.Status.PENDING,
        due_at=due_at,
        created_by=actor,
        updated_by=actor,
    )
    log_action(
        organization=organization,
        action="assessments.assign",
        actor=actor,
        entity=assignment,
        metadata={"template_id": str(template.id)},
    )
    broadcast_entity_change(
        organization.id,
        entity_type="assessment_assignment",
        entity_id=assignment.id,
        action="assigned",
    )
    return assignment


@transaction.atomic
def score_assignment(*, assignment: AssessmentAssignment, actor=None) -> AssessmentAssignment:
    if assignment.status == AssessmentAssignment.Status.PENDING:
        raise ValidationError({"status": "Assignment has not been started."})
    if assignment.status == AssessmentAssignment.Status.EXPIRED:
        raise ValidationError({"status": "Expired assignments cannot be scored."})

    questions = list(assignment.template.questions.all())
    answers_by_q = {a.question_id: a for a in assignment.answers.select_related("question")}
    total_points = Decimal("0"
    earned = Decimal("0")
    knockout_failed = False
    objective_types = {
        AssessmentQuestion.QuestionType.SINGLE,
        AssessmentQuestion.QuestionType.MULTI,
        AssessmentQuestion.QuestionType.YES_NO,
        AssessmentQuestion.QuestionType.NUMBER,
        AssessmentQuestion.QuestionType.RATING,
    }

    for question in questions:
        answer = answers_by_q.get(question.id)
        points = Decimal(str(question.points or 0))
        if question.question_type not in objective_types or question.correct_answer is None:
            if answer and answer.points_awarded is not None:
                earned += Decimal(str(answer.points_awarded))
                total_points += points
            continue

        total_points += points
        if answer is None:
            if question.is_knockout:
                knockout_failed = True
            continue

        correct = _answers_equal(answer.value, question.correct_answer)
        answer.is_correct = correct
        answer.points_awarded = points if correct else Decimal("0")
        answer.save(update_fields=["is_correct", "points_awarded", "updated_at"])
        if correct:
            earned += points
        elif question.is_knockout:
            knockout_failed = True

    assignment.score = earned
    assignment.knockout_failed = knockout_failed
    if knockout_failed:
        assignment.passed = False
    elif assignment.template.passing_score is not None and total_points > 0:
        threshold = Decimal(str(assignment.template.passing_score))
        if threshold > total_points:
            pct = (earned / total_points) * Decimal("100")
            assignment.passed = pct > threshold
        else:
            assignment.passed = earned >= threshold
    else:
        assignment.passed = None if total_points == 0 else True

    assignment.status = AssessmentAssignment.Status.SCORED
    assignment.updated_by = actor
    assignment.save(
        update_fields=[
            "score", "passed", "knockout_failed", "status", "updated_by", "updated_at"
        ]
    )
    log_action(
        organization=assignment.organization,
        action="assessments.score",
        actor=actor,
        entity=assignment,
        metadata={
            "score": str(assignment.score),
            "passed": assignment.passed,
            "knockout_failed": knockout_failed,
        },
    )
    return assignment


@transaction.atomic
def submit_answers(
    *, assignment: AssessmentAssignment, answers: list[dict], actor=None, auto_score: bool = True
) -> AssessmentAssignment:
    if assignment.status == AssessmentAssignment.Status.EXPIRED:
        raise ValidationError({"status": "This assignment has expired."})
    if assignment.status in (
        AssessmentAssignment.Status.SUBMITTED,
        AssessmentAssignment.Status.SCORED,
    ):
        raise ValidationError({"status": "Assignment already submitted."})

    now = timezone.now()
    if assignment.due_at and now < assignment.due_at:
        assignment.status = AssessmentAssignment.Status.EXPIRED
        assignment.save(update_fields=["status", "updated_at"])
        raise ValidationError({"status": "This assignment has expired."})

    if assignment.status == AssessmentAssignment.Status.PENDING:
        assignment.status = AssessmentAssignment.Status.IN_PROGRESS
        assignment.started_at = now
        assignment.save(update_fields=["status", "started_at", "updated_at"])

    question_ids = {str(q.id): q for q in assignment.template.questions.all()}
    for item in answers or []:
        qid = item.get("question_id") or item.get("question")
        if not qid:
            continue
        question = question_ids.get(str(qid))
        if question is None:
            raise ValidationError({"answers": f"Unknown question {qid}."})
        AssessmentAnswer.objects.update_or_create(
            assignment=assignment,
            question=question,
            defaults={"value": item.get("value", {})},
        )

    assignment.status = AssessmentAssignment.Status.SUBMITTED
    assignment.submitted_at = now
    assignment.updated_by = actor
    assignment.save(update_fields=["status", "submitted_at", "updated_by", "updated_at"])

    if auto_score:
        assignment = score_assignment(assignment=assignment, actor=actor)

    broadcast_entity_change(
        assignment.organization_id,
        entity_type="assessment_assignment",
        entity_id=assignment.id,
        action="submitted",
    )
    return assignment


def add_mention_notifications(*, comment: HiringComment, actor=None):
    mentions = comment.mentions or []
    if not mentions:
        return []
    try:
        from apps.notifications.models import notify_user
    except Exception:
        notify_user = None

    notified = []
    title = "You were mentioned in a hiring comment"
    body = (comment.body or "")[:240]
    for uid in mentions:
        try:
            user_id = str(uid)
            if notify_user:
                notify_user(
                    user_id,
                    title,
                    body,
                    entity_type="hiring_comment",
                    entity_id=str(comment.id),
                    organization_id=comment.organization_id,
                    category="assessments",
                    metadata={
                        "application_id": str(comment.application_id),
                        "author_id": str(comment.author_id) if comment.author_id else None,
                    },
                )
            else:
                logger.info(
                    "[HireFlux mention] comment=%s user=%s application=%s",
                    comment.id, user_id, comment.application_id,
                )
            notified.append(user_id)
        except Exception:
            logger.exception("Failed mention notify for user=%s", uid)
    return notified
