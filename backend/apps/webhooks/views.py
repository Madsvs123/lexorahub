import secrets

from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.common.permissions import HasEditorialPrivilege, IsOrganizationMember
from apps.webhooks.models import WebhookDelivery, WebhookEndpoint


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = [
            "id",
            "name",
            "url",
            "secret",
            "events",
            "is_active",
            "publications",
            "headers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
        extra_kwargs = {"secret": {"write_only": True}}


class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = "__all__"


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember, HasEditorialPrivilege]
    required_privilege = "api.manage"
    queryset = WebhookEndpoint.objects.all()

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else WebhookEndpoint.objects.none()

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.organization,
            secret=secrets.token_urlsafe(32),
        )


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = WebhookDelivery.objects.select_related("endpoint")
    filterset_fields = ["endpoint", "event", "success"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return (
            self.queryset.filter(endpoint__organization=org)
            if org
            else WebhookDelivery.objects.none()
        )
