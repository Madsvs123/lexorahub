from django.contrib import admin

from .models import (
    Offer,
    OfferApproval,
    OfferApprovalChain,
    OfferTemplate,
    OnboardingHandoff,
)


class OfferApprovalInline(admin.TabularInline):
    model = OfferApproval
    extra = 0
    raw_id_fields = ("approver",)


@admin.register(OfferTemplate)
class OfferTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "created_at")
    search_fields = ("name",)
    raw_id_fields = ("organization", "created_by", "updated_by")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "id", "candidate", "job", "status", "salary_amount", "salary_currency",
        "sent_at", "organization",
    )
    list_filter = ("status", "salary_period")
    search_fields = ("candidate__first_name", "candidate__last_name", "job__title")
    raw_id_fields = (
        "organization", "application", "candidate", "job", "template",
        "created_by", "updated_by",
    )
    inlines = [OfferApprovalInline]


@admin.register(OfferApproval)
class OfferApprovalAdmin(admin.ModelAdmin):
    list_display = ("offer", "approver", "order", "status", "decided_at")
    list_filter = ("status",)
    raw_id_fields = ("offer", "approver")


@admin.register(OfferApprovalChain)
class OfferApprovalChainAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_default", "created_at")
    list_filter = ("is_default",)
    search_fields = ("name",)
    raw_id_fields = ("organization", "created_by", "updated_by")


@admin.register(OnboardingHandoff)
class OnboardingHandoffAdmin(admin.ModelAdmin):
    list_display = ("offer", "assignee", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("offer", "assignee")
