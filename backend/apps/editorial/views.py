from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsOrganizationMember
from apps.editorial.models import (
    Assignment,
    Correction,
    EditorialComment,
    EditorialNote,
    WorkflowTransitionLog,
)
from apps.notifications.services import notify_user


class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ["id", "assigned_by", "created_at", "updated_at"]


class EditorialCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = EditorialComment
        fields = [
            "id",
            "entry",
            "author",
            "author_name",
            "parent",
            "body",
            "anchor",
            "mentions",
            "is_resolved",
            "resolved_by",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author", "resolved_by", "resolved_at", "created_at", "updated_at"]


class EditorialNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = EditorialNote
        fields = "__all__"
        read_only_fields = ["id", "author", "created_at", "updated_at"]


class CorrectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Correction
        fields = "__all__"
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]


class WorkflowTransitionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTransitionLog
        fields = "__all__"


class OrgEntryScopedMixin:
    def filter_by_org(self, qs, entry_field="entry_id"):
        org = getattr(self.request, "organization", None)
        if not org:
            return qs.none()
        return qs.filter(**{f"{entry_field}__organization": org})


class AssignmentViewSet(OrgEntryScopedMixin, viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Assignment.objects.select_related("entry", "assignee", "assigned_by")

    def get_queryset(self):
        return self.filter_by_org(self.queryset)

    def perform_create(self, serializer):
        assignment = serializer.save(assigned_by=self.request.user)
        notify_user(
            assignment.assignee_id,
            title="New assignment",
            body=assignment.instructions or f"Assigned: {assignment.entry.title}",
            entity_type="assignment",
            entity_id=str(assignment.id),
            organization_id=str(assignment.entry.organization_id),
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        assignment = self.get_object()
        assignment.is_complete = True
        assignment.completed_at = timezone.now()
        assignment.save(update_fields=["is_complete", "completed_at", "updated_at"])
        return Response(AssignmentSerializer(assignment).data)


class EditorialCommentViewSet(OrgEntryScopedMixin, viewsets.ModelViewSet):
    serializer_class = EditorialCommentSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = EditorialComment.objects.select_related("author").prefetch_related("mentions")
    filterset_fields = ["entry", "is_resolved"]

    def get_queryset(self):
        return self.filter_by_org(self.queryset)

    def perform_create(self, serializer):
        comment = serializer.save(author=self.request.user)
        for user in comment.mentions.all():
            notify_user(
                user.id,
                title="You were mentioned",
                body=comment.body[:200],
                entity_type="content_entry",
                entity_id=str(comment.entry_id),
                organization_id=str(comment.entry.organization_id),
            )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        comment = self.get_object()
        comment.is_resolved = False
        comment.resolved_by = request.user
        comment.resolved_at = timezone.now()
        comment.save()
        return Response(EditorialCommentSerializer(comment).data)


class EditorialNoteViewSet(OrgEntryScopedMixin, viewsets.ModelViewSet):
    serializer_class = EditorialNoteSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = EditorialNote.objects.select_related("author")
    filterset_fields = ["entry", "note_type"]

    def get_queryset(self):
        return self.filter_by_org(self.queryset)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CorrectionViewSet(OrgEntryScopedMixin, viewsets.ModelViewSet):
    serializer_class = CorrectionSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Correction.objects.all()

    def get_queryset(self):
        return self.filter_by_org(self.queryset)

    def perform_create(self, serializer):
        correction = serializer.save(created_by=self.request.user)
        entry = correction.entry
        entry.status = "correction"
        entry.save(update_fields=["status", "updated_at"])
