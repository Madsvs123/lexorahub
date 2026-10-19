from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.collaboration.models import CollaborationSession, DocumentConflict
from apps.common.permissions import IsOrganizationMember


class CollaborationSessionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = CollaborationSession
        fields = [
            "id",
            "entry",
            "user",
            "user_name",
            "client_id",
            "cursor",
            "selection",
            "last_seen_at",
            "is_active",
        ]


class DocumentConflictSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentConflict
        fields = "__all__"
        read_only_fields = ["id", "reported_by", "created_at", "updated_at"]


class CollaborationSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CollaborationSessionSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = CollaborationSession.objects.select_related("user")
    filterset_fields = ["entry", "is_active"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(entry__organization=org) if org else CollaborationSession.objects.none()


class DocumentConflictViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentConflictSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = DocumentConflict.objects.all()

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(entry__organization=org) if org else DocumentConflict.objects.none()

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        conflict = self.get_object()
        conflict.resolved = False
        conflict.resolution = request.data.get("resolution", {})
        conflict.save(update_fields=["resolved", "resolution", "updated_at"])
        return Response(DocumentConflictSerializer(conflict).data)
