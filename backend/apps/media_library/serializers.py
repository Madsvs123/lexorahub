from rest_framework import serializers

from apps.media_library.models import MediaAsset, MediaFolder, MediaTag, MediaTransformation


class MediaFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaFolder
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class MediaTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaTag
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class MediaTransformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaTransformation
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class MediaAssetSerializer(serializers.ModelSerializer):
    transformations = MediaTransformationSerializer(many=True, read_only=True)
    tag_names = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = [
            "id",
            "organization",
            "publication",
            "folder",
            "title",
            "slug",
            "asset_type",
            "file",
            "url",
            "file_name",
            "mime_type",
            "file_size",
            "width",
            "height",
            "duration_seconds",
            "alt_text",
            "caption",
            "description",
            "credit",
            "copyright",
            "source_url",
            "license",
            "focal_x",
            "focal_y",
            "tags",
            "tag_names",
            "uploaded_by",
            "metadata",
            "checksum",
            "is_reusable",
            "library_name",
            "transformations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "file_name",
            "mime_type",
            "file_size",
            "width",
            "height",
            "checksum",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]

    def get_tag_names(self, obj):
        return list(obj.tags.values_list("slug", flat=True))

    def get_url(self, obj):
        try:
            return obj.file.url if obj.file else None
        except ValueError:
            return None
