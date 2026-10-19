"""Offer ViewSets: templates, chains, offers, onboarding handoffs."""

from __future__ import annotations

from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.mixins import OrgQuerysetMixin
from apps.core.permissions import HasPerm, IsOrgMember, IsStaffUser

from . import services
from .models import Offer, OfferApprovalChain, OfferTemplate, OnboardingHandoff
from .serializers import (
    OfferActionSerializer,
    OfferApprovalChainSerializer,
    OfferApprovalSerializer,
    OfferCreateSerializer,
    OfferListSerializer,
    OfferSerializer,
    OfferTemplateSerializer,
    OnboardingHandoffSerializer,
)


class OfferFilter(filters.FilterSet
    status = filters.CharFilter(field_name="status")
    application = filters.UUIDFilter(field_name="application_id")
    job = filters.UUIDFilter(field_name="job_id")
    candidate = filters.UUIDFilter(field_name="candidate_id")

    class Meta:
        model = Offer
        fields = ["status", "application", "job", "candidate"]


class OfferTemplateViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = OfferTemplateSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "offers.manage"
    queryset = OfferTemplate.objects.all()
    search_fields = ("name",)

    def get_permissions(self):
        self.permission_required = (
            "offers.view" if self.action in ("list", "retrieve") else "offers.manage"
        )
        return super().get_permissions()


class OfferApprovalChainViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = OfferApprovalChainSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "offers.manage"
    queryset = OfferApprovalChain.objects.all()
    search_fields = ("name",)

    def get_permissions(self):
        self.permission_required = (
            "offers.view" if self.action in ("list", "retrieve") else "offers.manage"
        )
        return super().get_permissions()


class OfferViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "offers.view"
    filterset_class = OfferFilter
    queryset = Offer.objects.select_related(
        "candidate", "job", "application", "template"
    ).prefetch_related("approvals__approver")
    search_fields = ("candidate__first_name", "candidate__last_name", "job__title")
    ordering_fields = ("created_at", "sent_at", "expires_at", "salary_amount")

    def get_permissions(self):
        manage = {
            "create", "update", "partial_update", "destroy", "submit_approval",
            "send", "withdraw", "start_onboarding", "accept", "reject",
        }
        approve = {"approve", "reject_approval"}
        if self.action in manage:
            self.permission_required = "offers.manage"
        elif self.action in approve:
            self.permission_required = "offers.approve"
        else:
            self.permission_required = "offers.view"
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "list":
            return OfferListSerializer
        if self.action == "create":
            return OfferCreateSerializer
        return OfferSerializer

    def perform_create(self, serializer):
        from apps.pipelines.models import Application
        from rest_framework.exceptions import ValidationError

        org = self.get_organization()
        application = serializer.validated_data["application"]
        if getattr(application, "organization_id", None) != org.id:
            application = Application.objects.for_org(org).filter(pk=application.pk).first()
            if application is None:
                raise ValidationError({"application": "Application not found."})
        benefits = serializer.validated_data.get("benefits")
        template = serializer.validated_data.get("template")
        if not benefits and template and template.default_benefits:
            benefits = template.default_benefits
        offer = serializer.save(
            organization=org,
            application=application,
            candidate=application.candidate,
            job=application.job,
            benefits=benefits or {},
            created_by=self.request.user,
            updated_by=self.request.user,
        )
        serializer.instance = offer

    @action(detail=True, methods=["post"], url_path="submit-approval")
    def submit_approval(self, request, pk=None):
        offer = self.get_object()
        ser = OfferActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        chain = None
        if data.get("chain_id"):
            chain = (
                OfferApprovalChain.objects.for_org(request.organization)
                .filter(pk=data["chain_id"])
                .first()
            )
        offer, approvals = services.submit_offer_for_approval(
            offer=offer,
            actor=request.user,
            chain=chain,
            approver_ids=data.get("approver_ids") or None,
        )
        return Response(
            {
                "offer": OfferSerializer(offer, context={"request": request}).data,
                "approvals": OfferApprovalSerializer(approvals, many=True).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        offer = self.get_object()
        ser = OfferActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer, approval = services.approve_step(
            offer=offer, actor=request.user, comment=ser.validated_data.get("comment", "")
        )
        return Response(
            {
                "offer": OfferSerializer(offer, context={"request": request}).data,
                "approval": OfferApprovalSerializer(approval).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="reject-approval")
    def reject_approval(self, request, pk=None):
        offer = self.get_object()
        ser = OfferActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer, approval = services.reject_approval_step(
            offer=offer, actor=request.user, comment=ser.validated_data.get("comment", "")
        )
        return Response(
            {
                "offer": OfferSerializer(offer, context={"request": request}).data,
                "approval": OfferApprovalSerializer(approval).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="send")
    def send(self, request, pk=None):
        offer = services.send_offer(offer=self.get_object(), actor=request.user)
        return Response(OfferSerializer(offer, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, pk=None):
        ser = OfferActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer = services.accept_offer(
            offer=self.get_object(),
            actor=request.user,
            candidate_message=ser.validated_data.get("candidate_message", ""),
        )
        return Response(OfferSerializer(offer, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        ser = OfferActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        offer = services.reject_offer(
            offer=self.get_object(),
            actor=request.user,
            candidate_message=ser.validated_data.get("candidate_message", ""),
        )
        return Response(OfferSerializer(offer, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        offer = self.get_object()
        if offer.status in (
            Offer.Status.SENT, Offer.Status.EXPIRED, Offer.Status.WITHDRAWN
        ):
            return Response(
                {"detail": f"Cannot withdraw offer in status '{offer.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        offer.status = Offer.Status.WITHDRAWN
        offer.updated_by = request.user
        offer.save(update_fields=["status", "updated_by", "updated_at"])
        return Response(OfferSerializer(offer, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="start-onboarding")
    def start_onboarding(self, request, pk=None):
        offer = self.get_object()
        ser = OfferActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        assignee = None
        if data.get("assignee"):
            from django.contrib.auth import get_user_model

            assignee = get_user_model().objects.filter(pk=data["assignee"]).first()
        handoff = services.start_onboarding_handoff(
            offer=offer,
            assignee=assignee,
            checklist=data.get("checklist"),
            actor=request.user,
            notes=data.get("notes", ""),
        )
        return Response(OnboardingHandoffSerializer(handoff).data)


class OnboardingHandoffViewSet(OrgQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = OnboardingHandoffSerializer
    permission_classes = [IsAuthenticated, IsOrgMember, IsStaffUser, HasPerm]
    permission_required = "offers.manage"
    queryset = OnboardingHandoff.objects.select_related("offer", "assignee")
    org_field = "offer__organization"
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        self.permission_required = (
            "offers.view" if self.action in ("list", "retrieve") else "offers.manage"
        )
        return super().get_permissions()

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if org is None:
            return OnboardingHandoff.objects.none()
        return self.queryset.filter(offer__organization=org)
