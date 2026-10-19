from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.media_library.views import MediaAssetViewSet, MediaFolderViewSet, MediaTagViewSet

router = DefaultRouter()
router.register("folders", MediaFolderViewSet, basename="media-folder")
router.register("tags", MediaTagViewSet, basename="media-tag")
router.register("files", MediaAssetViewSet, basename="media-asset")

urlpatterns = [path("", include(router.urls))]
