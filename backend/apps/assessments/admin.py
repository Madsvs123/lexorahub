from django.contrib import admin

from .models import (
    AssessmentAnswer,
    AssessmentAssignment,
    AssessmentQuestion,
    AssessmentTemplate,
    CandidateRating,
    HiringComment,
)


class AssessmentQuestionInline(admin.TabularInline):
    model = AssessmentQuestion
    extra = 0


@admin.register(AssessmentTemplate)
class AssessmentTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name", "organization", "assessment_type", "time_limit_minutes", "passing_score"
    )
    list_filter = ("assessment_type",)
    search_fields = ("name",)
    raw_id_fields = ("organization", "created_by", "updated_by")
    inlines = [AssessmentQuestionInline]


@admin.register(AssessmentQuestion)
class AssessmentQuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "template", "question_type", "is_required", "is_knockout", "order")
    list_filter = ("question_type", "is_knockout")
    raw_id_fields = ("template",)


class AssessmentAnswerInline(admin.TabularInline):
    model = AssessmentAnswer
    extra = 0
    raw_id_fields = ("question",)


@admin.register(AssessmentAssignment)
class AssessmentAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "candidate", "job", "template", "status", "score", "passed",
        "knockout_failed", "due_at",
    )
    list_filter = ("status", "passed", "knockout_failed")
    raw_id_fields = (
        "organization", "application", "candidate", "job", "template",
        "created_by", "updated_by",
    )
    inlines = [AssessmentAnswerInline]


@admin.register(CandidateRating)
class CandidateRatingAdmin(admin.ModelAdmin):
    list_display = ("application", "rater", "overall", "organization", "created_at")
    raw_id_fields = ("organization", "application", "rater")


@admin.register(HiringComment)
class HiringCommentAdmin(admin.ModelAdmin):
    list_display = ("application", "author", "parent", "created_at")
    search_fields = ("body",)
    raw_id_fields = ("organization", "application", "author", "parent")
