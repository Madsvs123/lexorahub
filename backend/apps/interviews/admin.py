from django.contrib import admin

from .models import (
    Interview,
    InterviewDecisionSummary,
    InterviewerAssignment,
    InterviewerAvailability,
    InterviewKit,
    InterviewPanel,
    Scorecard,
)


class InterviewerAssignmentInline(admin.TabularInline):
    model = InterviewerAssignment
    extra = 0
    raw_id_fields = ("interviewer",)


class ScorecardInline(admin.TabularInline):
    model = Scorecard
    extra = 0
    raw_id_fields = ("interviewer",)


@admin.register(InterviewKit)
class InterviewKitAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "job", "created_at")
    search_fields = ("name",)
    raw_id_fields = ("organization", "job", "created_by", "updated_by")


@admin.register(InterviewPanel)
class InterviewPanelAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "created_at")
    search_fields = ("name",)
    raw_id_fields = ("organization", "created_by", "updated_by")
    filter_horizontal = ("members",)


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = (
        "id", "candidate", "job", "interview_type", "status", "scheduled_start", "organization"
    )
    list_filter = ("status", "interview_type")
    search_fields = ("candidate__first_name", "candidate__last_name", "job__title")
    raw_id_fields = (
        "organization", "application", "job", "candidate", "kit", "panel",
        "organizer", "created_by", "updated_by",
    )
    inlines = [InterviewerAssignmentInline, ScorecardInline]


@admin.register(InterviewerAvailability)
class InterviewerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("user", "weekday", "start_time", "end_time", "timezone", "organization")
    list_filter = ("weekday",)
    raw_id_fields = ("organization", "user")


@admin.register(Scorecard)
class ScorecardAdmin(admin.ModelAdmin):
    list_display = ("interview", "interviewer", "overall_rating", "recommendation", "submitted_at")
    list_filter = ("recommendation",)
    raw_id_fields = ("interview", "interviewer")


@admin.register(InterviewDecisionSummary)
class InterviewDecisionSummaryAdmin(admin.ModelAdmin):
    list_display = ("interview", "decision", "average_rating", "decided_by", "created_at")
    list_filter = ("decision",)
    raw_id_fields = ("interview", "decided_by")


@admin.register(InterviewerAssignment)
class InterviewerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("interview", "interviewer", "role", "response", "feedback_submitted")
    list_filter = ("role", "response", "feedback_submitted")
    raw_id_fields = ("interview", "interviewer")
