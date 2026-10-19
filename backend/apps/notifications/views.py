from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.consumers import UserNotificationConsumer  # noqa: F401


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "title",
            "body",
            "category",
            "entity_type",
            "entity_id",
            "link",
            "is_read",
            "read_at",
            "metadata",
            "created_at",
        ]


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Notification.objects.all()

    def get_queryset(self):
        return self.queryset.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.read_at = timezone.now()
        n.save(update_fields=["is_read", "read_at", "updated_at"])
        return Response(NotificationSerializer(n).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=True).update(is_read=True, read_at=timezone.now())
        return Response({"updated": updated})
