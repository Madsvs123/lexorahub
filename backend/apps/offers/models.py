"""
HireFlux offer templates, offers, approvals, and onboarding handoffs.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import AuditedModel, TenantModel, TimeStampedModel


class OfferTemplate(TenantModel, AuditedModel):
    name = models.CharField(max_length=200)
    body_html = models.TextField(blank=True, default="")
    default_benefits = models.JSONField(default=dict, blank=True)
    variables = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_offer_template_org_name",
            ),
        ]

    def __str__(self):
        return self.name


class Offer(TenantModel, AuditedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING_APPROVAL = "pending_approval", "Pending approval"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        WITHDRAWN = "withdrawn", "Withdrawn"
        NEGOTIATING = "negotiating", "Negotiating"

    class SalaryPeriod(models.TextChoices):
        ANNUAL = "annual", "Annual"
        MONTHLY = "monthly", "Monthly"
        HOURLY = "hourly", "Hourly"

    application = models.ForeignKey(
        "pipelines.Application", on_delete=models.CASCADE, related_name="offers"
    )
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.CASCADE, related_name="offers"
    )
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.CASCADE, related_name="offers"
    )
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    salary_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    salary_currency = models.CharField(max_length=8, default="USD")
    salary_period = models.CharField(
        max_length=16, choices=SalaryPeriod.choices, default=SalaryPeriod.ANNUAL
    )
    equity = models.CharField(max_length=240, blank=True, default="")
    bonus = models.CharField(max_length=240, blank=True, default="")
    benefits = models.JSONField(default=dict, blank=True)
    start_date = models.DateField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    template = models.ForeignKey(
        OfferTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offers",
    )
    offer_letter_html = models.TextField(blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    candidate_message = models.TextField(blank=True, default="")
    negotiation_notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["application", "status"]),
        ]

    def __str__(self):
        return f"Offer {self.pk} ({self.status})"


class OfferApproval(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name="approvals")
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offer_approvals",
    )
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    comment = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("order", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=["offer", "approver", "order"],
                name="uniq_offer_approval_step",
            ),
        ]

    def __str__(self):
        return f"Approval {self.offer_id} #{self.order} ({self.status})"


class OfferApprovalChain(TenantModel, AuditedModel):
    name = models.CharField(max_length=200)
    steps = models.JSONField(default=list, blank=True)
    is_default = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ("-is_default", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="uniq_offer_approval_chain_org_name",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.is_default:
            OfferApprovalChain.objects.filter(
                organization_id=self.organization_id, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)


class OnboardingHandoff(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    offer = models.OneToOneField(
        Offer, on_delete=models.CASCADE, related_name="onboarding_handoff"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_handoffs",
    )
    checklist = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Onboarding {self.offer_id} ({self.status})"
