from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsOrganizationMember
from apps.content.models import ContentEntry
from apps.scheduling.models import (
    Campaign,
    ContentQueue,
    EditorialCalendarEvent,
    QueueItem,
    ScheduledPublication,
)
from apps.scheduling.tasks import process_due_publications


class EditorialCalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialCalendarEvent
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_by", "created_at", "updated_at"]


class QueueItemSerializer(serializers.ModelSerializer):
    entry_title = serializers.CharField(source="entry.title", read_only=True)

    class Meta:
        model = QueueItem
        fields = "__all__"


class ContentQueueSerializer(serializers.ModelSerializer):
    items = QueueItemSerializer(many=True, read_only=True)

    class Meta:
        model = ContentQueue
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class ScheduledPublicationSerializer(serializers.ModelSerializer):
    entry_title = serializers.CharField(source="entry.title", read_only=True)

    class Meta:
        model = ScheduledPublication
        fields = "__all__"
        read_only_fields = ["id", "is_processed", "processed_at", "created_by", "created_at", "updated_at"]


class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = EditorialCalendarEventSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = EditorialCalendarEvent.objects.select_related("publication", "entry", "channel")
    filterset_fields = ["publication", "event_type", "channel"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        qs = self.queryset.filter(organization=org) if org else EditorialCalendarEvent.objects.none()
        start = self.request.query_params.get("start")
        end = self.request.query_params.get("end")
        if start:
            qs = qs.filter(starts_at__lte=start)
        if end:
            qs = qs.filter(starts_at__lte=end)
        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization, created_by=self.request.user)


class ContentQueueViewSet(viewsets.ModelViewSet):
    serializer_class = ContentQueueSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = ContentQueue.objects.prefetch_related("items__entry")

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else ContentQueue.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)

    @action(detail=True, methods=["post"])
    def add_entry(self, request, pk=None):
        queue = self.get_object()
        entry_id = request.data.get("entry")
        sort_order = request.data.get("sort_order", queue.items.count())
        item, _ = QueueItem.objects.get_or_create(
            queue=queue, entry_id=request.data.get("entry_id"), defaults={"sort_order": sort_order}
        )
        return Response(QueueItemSerializer(item).data)


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Campaign.objects.prefetch_related("entries", "channels")

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else Campaign.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)


class ScheduledPublicationViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduledPublicationSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = ScheduledPublication.objects.select_related("entry")

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return (
            self.queryset.filter(entry__organization=org)
            if org
            else ScheduledPublication.objects.none()
        )

    def perform_create(self, serializer):
        schedule = serializer.save(created_by=self.request.user)
        entry = schedule.entry
        entry.status = ContentEntry.Status.SCHEDULED
        entry.scheduled_for = schedule.publish_at
        entry.embargo_until = schedule.embargo_until
        entry.expires_at = schedule.unpublish_at
        entry.save(update_fields=["status", "scheduled_for", "expires_at", "updated_at"])

    @action(detail=False, methods=["post"])
    def process_due(self, request):
        process_due_publications.delay()
        return Response({"queued": True, "at": timezone.now()})
