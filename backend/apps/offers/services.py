"""Offer approval, send/accept/reject, expiry, and onboarding handoff services."""

from __future__ import annotations

import logging
from string import Template

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import log_action
from apps.core.realtime import broadcast_entity_change

from .models import Offer, OfferApproval, OfferApprovalChain, OnboardingHandoff

logger = logging.getLogger(__name__)

DEFAULT_ONBOARDING_CHECKLIST = [
    {"key": "welcome_email", "label": "Send welcome email", "done": False},
    {"key": "equipment", "label": "Order equipment", "done": False},
    {"key": "accounts", "label": "Provision accounts", "done": False},
    {"key": "paperwork", "label": "Collect paperwork", "done": False},
]


def _render_offer_letter(offer: Offer) -> str
    template_html = ""
    if offer.template_id and offer.template:
        template_html = offer.template.body_html or ""
    if offer.offer_letter_html:
        template_html = offer.offer_letter_html
    if not template_html:
        template_html = (
            "<h1>Offer of Employment</h1>"
            "<p>Dear $candidate_name,</p>"
            "<p>We are pleased to offer you the position of <strong>$job_title</strong>.</p>"
            "<p>Salary: $salary_amount $salary_currency ($salary_period)</p>"
            "<p>Start date: $start_date</p>"
        )
    mapping = {
        "candidate_name": getattr(offer.candidate, "full_name", "") or "",
        "job_title": getattr(offer.job, "title", "") or "",
        "salary_amount": str(offer.salary_amount or ""),
        "salary_currency": offer.salary_currency or "",
        "salary_period": offer.salary_period or "",
        "equity": offer.equity or "",
        "bonus": offer.bonus or "",
        "start_date": str(offer.start_date or ""),
        "expires_at": offer.expires_at.isoformat() if offer.expires_at else "",
    }
    try:
        return Template(template_html).safe_substitute(**mapping)
    except Exception:
        return template_html


def _resolve_chain_approvers(*, organization, chain: OfferApprovalChain | None, actor):
    if chain is None:
        chain = OfferApprovalChain.objects.filter(
            organization=organization, is_default=True
        ).first()
    steps = list((chain.steps if chain else None) or [])
    if not steps:
        return [actor.id] if actor else []

    user_ids = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        uid = step.get("user_id") or step.get("user")
        if uid:
            user_ids.append(uid)
            continue
        role = step.get("role")
        if role:
            try:
                from apps.accounts.models import Membership

                member = (
                    Membership.objects.filter(
                        organization=organization, is_active=True, role__slug=role
                    )
                    .select_related("user")
                    .first()
                )
                if member:
                    user_ids.append(member.user_id)
                    continue
            except Exception:
                pass
            if actor:
                user_ids.append(actor.id)
    return user_ids


def _move_application_to_hired(*, application, actor=None):
    try:
        from apps.pipelines.models import PipelineStage
        from apps.pipelines.services import move_application

        pipeline = application.pipeline
        hired_stage = (
            pipeline.stages.filter(stage_type=PipelineStage.StageType.HIRED)
            .order_by("order")
            .first()
        )
        if hired_stage is None:
            return None
        return move_application(
            application, hired_stage, actor, "Offer accepted"
        )
    except Exception:
        logger.exception(
            "Failed to move application %s to hired after offer accept",
            getattr(application, "id", None),
        )
        try:
            from apps.pipelines.models import Application

            if hasattr(application, "status"):
                application.status = Application.Status.HIRED
                fields = ["status", "updated_at"]
                if hasattr(application, "hired_at"):
                    application.hired_at = timezone.now()
                    fields.append("hired_at")
                application.save(update_fields=fields)
        except Exception:
            pass
        return None


@transaction.atomic
def submit_offer_for_approval(
    *, offer: Offer, actor=None, chain: OfferApprovalChain | None = None, approver_ids: list | None = None
):
    if offer.status not in (Offer.Status.DRAFT, Offer.Status.NEGOTIATING):
        raise ValidationError(
            {"status": f"Cannot submit offer in status '{offer.status}' for approval."}
        )
    if offer.salary_amount is None:
        raise ValidationError({"salary_amount": "Salary amount is required."})

    ids = list(approver_ids or [])
    if not ids:
        ids = _resolve_chain_approvers(
            organization=offer.organization, chain=chain, actor=actor
        )
    if not ids:
        raise ValidationError({"approvers": "At least one approver is required."})

    offer.status = Offer.Status.PENDING_APPROVAL
    offer.updated_by = actor
    if not offer.offer_letter_html:
        offer.offer_letter_html = _render_offer_letter(offer)
    offer.save(update_fields=["status", "offer_letter_html", "updated_by", "updated_at"])

    offer.approvals.all().delete()
    approvals = []
    for order, uid in enumerate(ids):
        approvals.append(
            OfferApproval.objects.create(
                offer=offer,
                approver_id=uid,
                order=order,
                status=OfferApproval.Status.PENDING,
            )
        )

    log_action(
        organization=offer.organization,
        action="offers.submit_approval",
        actor=actor,
        entity=offer,
        metadata={"approver_ids": [str(i) for i in ids]},
    )
    broadcast_entity_change(
        offer.organization_id, entity_type="offer", entity_id=offer.id, action="pending_approval"
    )
    return offer, approvals


@transaction.atomic
def approve_step(*, offer: Offer, actor, comment: str = ""):
    if offer.status != Offer.Status.PENDING_APPROVAL:
        raise ValidationError({"status": "Offer is not pending approval."})

    approval = (
        offer.approvals.filter(status=OfferApproval.Status.PENDING).order_by("order").first()
    )
    if approval is None:
        raise ValidationError({"detail": "No pending approval steps."})

    if approval.approver_id != actor.id:
        own = offer.approvals.filter(
            approver=actor, status=OfferApproval.Status.PENDING
        ).first()
        if own is None:
            raise ValidationError({"detail": "You are not the next approver."})
        if own.order != approval.order:
            raise ValidationError({"detail": "Earlier approval steps are still pending."})
        approval = own

    approval.status = OfferApproval.Status.APPROVED
    approval.comment = comment or ""
    approval.decided_at = timezone.now()
    approval.save(update_fields=["status", "comment", "decided_at", "updated_at"])

    still_pending = offer.approvals.filter(status=OfferApproval.Status.PENDING).exists()
    offer.updated_by = actor
    offer.save(update_fields=["updated_by", "updated_at"])
    log_action(
        organization=offer.organization,
        action="offers.approve_step",
        actor=actor,
        entity=offer,
        metadata={"approval_id": str(approval.id), "complete": not still_pending},
    )
    return offer, approval


@transaction.atomic
def reject_approval_step(*, offer: Offer, actor, comment: str = ""):
    if offer.status != Offer.Status.PENDING_APPROVAL:
        raise ValidationError({"status": "Offer is not pending approval."})
    approval = offer.approvals.filter(
        approver=actor, status=OfferApproval.Status.PENDING
    ).first()
    if approval is None:
        raise ValidationError({"detail": "No pending approval for this user."})
    approval.status = OfferApproval.Status.REJECTED
    approval.comment = comment or ""
    approval.decided_at = timezone.now()
    approval.save(update_fields=["status", "comment", "decided_at", "updated_at"])
    offer.status = Offer.Status.DRAFT
    offer.updated_by = actor
    offer.save(update_fields=["status", "updated_by", "updated_at"])
    log_action(
        organization=offer.organization,
        action="offers.reject_approval",
        actor=actor,
        entity=offer,
        metadata={"comment": comment},
    )
    return offer, approval


@transaction.atomic
def send_offer(*, offer: Offer, actor=None) -> Offer:
    if offer.status not in (
        Offer.Status.PENDING_APPROVAL,
        Offer.Status.DRAFT,
        Offer.Status.NEGOTIATING,
    ):
        raise ValidationError({"status": f"Cannot send offer from status '{offer.status}'."})
    if offer.status == Offer.Status.PENDING_APPROVAL:
        pending = offer.approvals.filter(status=OfferApproval.Status.PENDING).exists()
        rejected = offer.approvals.filter(status=OfferApproval.Status.REJECTED).exists()
        if pending and rejected:
            raise ValidationError(
                {"status": "All approval steps must be approved before sending."}
            )

    offer.offer_letter_html = _render_offer_letter(offer)
    offer.status = Offer.Status.SENT
    offer.sent_at = timezone.now()
    offer.updated_by = actor
    offer.save(
        update_fields=["offer_letter_html", "status", "sent_at", "updated_by", "updated_at"]
    )
    log_action(organization=offer.organization, action="offers.send", actor=actor, entity=offer)
    broadcast_entity_change(
        offer.organization_id, entity_type="offer", entity_id=offer.id, action="sent"
    )
    try:
        from apps.notifications.models import notify_user

        if offer.candidate.user_id:
            notify_user(
                offer.candidate.user_id,
                f"Offer: {offer.job.title}",
                "You have received a job offer.",
                entity_type="offer",
                entity_id=str(offer.id),
                organization_id=offer.organization_id,
                category="offers",
            )
    except Exception:
        logger.info("[HireFlux offer sent] offer=%s candidate=%s", offer.id, offer.candidate_id)
    return offer


@transaction.atomic
def accept_offer(*, offer: Offer, actor=None, candidate_message: str = "") -> Offer:
    if offer.status not in (Offer.Status.SENT, Offer.Status.NEGOTIATING):
        raise ValidationError({"status": f"Cannot accept offer in status '{offer.status}'."})
    if offer.expires_at and timezone.now() < offer.expires_at:
        offer.status = Offer.Status.EXPIRED
        offer.save(update_fields=["status", "updated_at"])
        raise ValidationError({"status": "This offer has expired."})

    offer.status = Offer.Status.ACCEPTED
    offer.responded_at = timezone.now()
    offer.candidate_message = candidate_message or offer.candidate_message
    offer.updated_by = actor
    offer.save(
        update_fields=[
            "status", "responded_at", "candidate_message", "updated_by", "updated_at"
        ]
    )
    _move_application_to_hired(application=offer.application, actor=actor)
    start_onboarding_handoff(offer=offer, actor=actor)
    log_action(organization=offer.organization, action="offers.accept", actor=actor, entity=offer)
    broadcast_entity_change(
        offer.organization_id, entity_type="offer", entity_id=offer.id, action="accepted"
    )
    return offer


@transaction.atomic
def reject_offer(*, offer: Offer, actor=None, candidate_message: str = "") -> Offer:
    if offer.status not in (Offer.Status.SENT, Offer.Status.NEGOTIATING):
        raise ValidationError({"status": f"Cannot reject offer in status '{offer.status}'."})
    offer.status = Offer.Status.REJECTED
    offer.responded_at = timezone.now()
    offer.candidate_message = candidate_message or offer.candidate_message
    offer.updated_by = actor
    offer.save(
        update_fields=[
            "status", "responded_at", "candidate_message", "updated_by", "updated_at"
        ]
    )
    log_action(organization=offer.organization, action="offers.reject", actor=actor, entity=offer)
    broadcast_entity_change(
        offer.organization_id, entity_type="offer", entity_id=offer.id, action="rejected"
    )
    return offer


def expire_offers(*, organization=None) -> int:
    now = timezone.now()
    qs = Offer.objects.filter(
        status__in=[Offer.Status.SENT, Offer.Status.NEGOTIATING],
        expires_at__isnull=False,
        expires_at__gt=now,
    )
    if organization is not None:
        qs = qs.filter(organization=organization)
    return qs.update(status=Offer.Status.EXPIRED)


@transaction.atomic
def start_onboarding_handoff(
    *, offer: Offer, assignee=None, checklist: list | None = None, actor=None, notes: str = ""
) -> OnboardingHandoff:
    if offer.status != Offer.Status.ACCEPTED:
        raise ValidationError({"status": "Onboarding handoff requires an accepted offer."})

    handoff, created = OnboardingHandoff.objects.get_or_create(
        offer=offer,
        defaults={
            "assignee": assignee or actor,
            "checklist": checklist or list(DEFAULT_ONBOARDING_CHECKLIST),
            "status": OnboardingHandoff.Status.IN_PROGRESS,
            "notes": notes or "",
        },
    )
    if not created:
        changed = False
        if assignee is not None:
            handoff.assignee = assignee
            changed = True
        if checklist is not None:
            handoff.checklist = checklist
            changed = True
        if notes:
            handoff.notes = notes
            changed = True
        if handoff.status == OnboardingHandoff.Status.PENDING:
            handoff.status = OnboardingHandoff.Status.IN_PROGRESS
            changed = True
        if changed:
            handoff.save()

    log_action(
        organization=offer.organization,
        action="offers.onboarding_start",
        actor=actor,
        entity=offer,
        metadata={"handoff_id": str(handoff.id)},
    )
    return handoff
