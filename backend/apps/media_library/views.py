import hashlib

from django.utils.text import slugify
from PIL import Image
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import IsOrganizationMember
from apps.media_library.models import MediaAsset, MediaFolder, MediaTag, MediaTransformation
from apps.media_library.serializers import (
    MediaAssetSerializer,
    MediaFolderSerializer,
    MediaTagSerializer,
    MediaTransformationSerializer,
)
from apps.media_library.services import detect_asset_type, generate_image_renditions


class MediaFolderViewSet(viewsets.ModelViewSet):
    serializer_class = MediaFolderSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = MediaFolder.objects.all()

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else MediaFolder.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)


class MediaTagViewSet(viewsets.ModelViewSet):
    serializer_class = MediaTagSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = MediaTag.objects.all()

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else MediaTag.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)


class MediaAssetViewSet(viewsets.ModelViewSet):
    serializer_class = MediaAssetSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    queryset = MediaAsset.objects.prefetch_related("tags", "transformations").filter(is_deleted=False)
    filterset_fields = ["asset_type", "folder", "publication", "library_name"]
    search_fields = ["title", "alt_text", "caption", "credit", "file_name"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else MediaAsset.objects.none()

    def perform_create(self, serializer):
        upload = self.request.FILES.get("file")
        extra = {
            "organization": self.request.organization,
            "uploaded_by": self.request.user,
        }
        if upload:
            extra["file_name"] = upload.name
            extra["mime_type"] = upload.content_type or ""
            extra["file_size"] = upload.size
            extra["asset_type"] = detect_asset_type(upload.content_type or "")
            if not serializer.validated_data.get("title"):
                extra["title"] = upload.name
            if not serializer.validated_data.get("slug"):
                extra["slug"] = slugify(upload.name)[:200]
            # checksum
            hasher = hashlib.sha256()
            for chunk in upload.chunks():
                hasher.update(chunk)
            upload.seek(0)
            extra["checksum"] = hasher.hexdigest()
            # image dimensions
            if (upload.content_type or "").startswith("image/"):
                try:
                    img = Image.open(upload)
                    extra["width"], extra["height"] = img.size
                    upload.seek(0)
                except Exception:
                    pass
        asset = serializer.save(**extra)
        if asset.asset_type == MediaAsset.AssetType.IMAGE:
            generate_image_renditions.delay(str(asset.id))

    @action(detail=True, methods=["post"])
    def set_focal_point(self, request, pk=None):
        asset = self.get_object()
        asset.focal_x = float(request.data.get("x", 0.5))
        asset.focal_y = float(request.data.get("y", 0.5))
        asset.save(update_fields=["focal_x", "focal_y", "updated_at"])
        return Response(MediaAssetSerializer(asset).data)

    @action(detail=True, methods=["post"])
    def regenerate_transforms(self, request, pk=None):
        asset = self.get_object()
        generate_image_renditions.delay(str(asset.id))
        return Response({"queued": True})

    @action(detail=False, methods=["get"])
    def libraries(self, request):
        org = request.organization
        names = (
            MediaAsset.objects.filter(organization=org, is_deleted=False)
            .exclude(library_name="")
            .values_list("library_name", flat=True)
            .distinct()
        )
        return Response(list(names))
