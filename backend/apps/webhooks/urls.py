from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.webhooks.views import WebhookDeliveryViewSet, WebhookEndpointViewSet

router = DefaultRouter()
router.register("endpoints", WebhookEndpointViewSet, basename="webhook-endpoint")
router.register("delivery", WebhookDeliveryViewSet, basename="webhook-delivery")

urlpatterns = [path("", include(router.urls))]
