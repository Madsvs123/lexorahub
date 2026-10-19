from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.i18n_cms.views import (
    LocaleConfigViewSet,
    LocaleFallbackView,
    TranslationGroupView,
    TranslationJobViewSet,
)

router = DefaultRouter()
router.register("jobs", TranslationJobViewSet, basename="translation-job")
router.register("locales", LocaleConfigViewSet, basename="locale-config")

urlpatterns = [
    path("fallbacks/", LocaleFallbackView.as_view(), name="locale-fallback"),
    path("groups/<uuid:entry_id>/", TranslationGroupView.as_view(), name="translation-group"),
    path("", include(router.urls)),
]
