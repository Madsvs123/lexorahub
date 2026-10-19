"""Serializers for offers, approvals, templates, and onboarding."""

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import (
    Offer,
    OfferApproval,
    OfferApprovalChain,
    OfferTemplate,
    OnboardingHandoff,
)


class OfferTemplateSerializer(serializers.ModelSerializer
    class Meta:
        model = OfferTemplate
        fields = (
            "id", "organization", "name", "body_html", "default_benefits", "variables",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "created_by", "updated_by", "created_at", "updated_at")


class OfferApprovalSerializer(serializers.ModelSerializer):
    approver_detail = UserSerializer(source="approver", read_only=True)

    class Meta:
        model = OfferApproval
        fields = (
            "id", "offer", "approver", "approver_detail", "order", "status",
            "comment", "decided_at", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "offer", "approver", "order", "status", "decided_at", "created_at", "updated_at"
        )


class OfferApprovalChainSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfferApprovalChain
        fields = (
            "id", "organization", "name", "steps", "is_default",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = ("id", "organization", "created_by", "updated_by", "created_at", "updated_at")


class OnboardingHandoffSerializer(serializers.ModelSerializer):
    assignee_detail = UserSerializer(source="assignee", read_only=True)

    class Meta:
        model = OnboardingHandoff
        fields = (
            "id", "offer", "assignee", "assignee_detail", "checklist", "status",
            "notes", "created_at", "updated_at",
        )
        read_only_fields = ("id", "offer", "created_at", "updated_at")


class OfferSerializer(serializers.ModelSerializer):
    approvals = OfferApprovalSerializer(many=True, read_only=True)
    onboarding_handoff = OnboardingHandoffSerializer(read_only=True)
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True, default="")
    job_title = serializers.CharField(source="job.title", read_only=True, default="")

    class Meta:
        model = Offer
        fields = (
            "id", "organization", "application", "candidate", "candidate_name", "job",
            "job_title", "status", "salary_amount", "salary_currency", "salary_period",
            "equity", "bonus", "benefits", "start_date", "expires_at", "template",
            "offer_letter_html", "sent_at", "responded_at", "candidate_message",
            "negotiation_notes", "approvals", "onboarding_handoff",
            "created_by", "updated_by", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "organization", "candidate", "job", "status", "sent_at", "responded_at",
            "created_by", "updated_by", "created_at", "updated_at", "approvals", "onboarding_handoff",
        )


class OfferListSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.email", read_only=True, default="")
    job_title = serializers.CharField(source="job.title", read_only=True, default="")

    class Meta:
        model = Offer
        fields = (
            "id", "application", "candidate", "candidate_name", "job", "job_title",
            "status", "salary_amount", "salary_currency", "salary_period", "start_date",
            "expires_at", "sent_at", "created_at",
        )


class OfferCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = (
            "application", "status", "salary_amount", "salary_currency", "salary_period", "equity",
            "bonus", "benefits", "start_date", "expires_at", "template",
            "offer_letter_html", "negotiation_notes",
        )


class OfferActionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    candidate_message = serializers.CharField(required=False, allow_blank=True, default="")
    chain_id = serializers.UUIDField(required=False, allow_null=True)
    approver_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    assignee = serializers.UUIDField(required=False, allow_null=True)
    checklist = serializers.JSONField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
