from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.delivery.views import (
    APIKeyViewSet,
    DeliveryContentView,
    PreviewTokenCreateView,
    delivery_homepage,
    delivery_menu,
)

router = DefaultRouter()
router.register("api-keys", APIKeyViewSet, basename="api-key")

urlpatterns = [
    path("entries/", DeliveryContentView.as_view(), name="delivery-content"),
    path("menus/", delivery_menu, name="delivery-menu"),
    path("homepage/", delivery_homepage, name="delivery-homepage"),
    path("preview-tokens/", PreviewTokenCreateView.as_view(), name="preview-token"),
    path("", include(router.urls)),
]
