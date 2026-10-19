from rest_framework import serializers

from apps.content.models import (
    BlockDefinition,
    Collection,
    ContentEntry,
    ContentRevision,
    ContentTypeDefinition,
    FieldDefinition,
    LandingPage,
    NavigationMenu,
    Series,
    Taxonomy,
    Term,
    Topic,
)
from apps.content.services import validate_custom_fields, validate_entry_body


class FieldDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldDefinition
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ContentTypeDefinitionSerializer(serializers.ModelSerializer):
    fields = FieldDefinitionSerializer(many=True, read_only=True)

    class Meta:
        model = ContentTypeDefinition
        fields = [
            "id",
            "organization",
            "publication",
            "name",
            "slug",
            "description",
            "icon",
            "is_singleton",
            "is_translatable",
            "allow_scheduling",
            "workflow_enabled",
            "default_status",
            "schema_version",
            "settings",
            "is_active",
            "fields",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class BlockDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockDefinition
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = [
            "id",
            "taxonomy",
            "parent",
            "name",
            "slug",
            "description",
            "metadata",
            "sort_order",
            "is_featured",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TaxonomySerializer(serializers.ModelSerializer):
    terms = TermSerializer(many=True, read_only=True)

    class Meta:
        model = Taxonomy
        fields = [
            "id",
            "organization",
            "publication",
            "name",
            "slug",
            "description",
            "is_hierarchical",
            "is_tag_like",
            "allow_multiple",
            "terms",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class ContentRevisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentRevision
        fields = [
            "id",
            "entry",
            "revision_number",
            "title",
            "body",
            "custom_fields",
            "seo",
            "social",
            "excerpt",
            "status",
            "created_by",
            "change_summary",
            "is_autosave",
            "created_at",
        ]
        read_only_fields = fields


class ContentEntryListSerializer(serializers.ModelSerializer):
    content_type_slug = serializers.CharField(source="content_type.slug", read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    author_names = serializers.SerializerMethodField()

    class Meta:
        model = ContentEntry
        fields = [
            "id",
            "publication",
            "content_type",
            "content_type_slug",
            "title",
            "slug",
            "locale",
            "status",
            "excerpt",
            "featured_image",
            "assigned_to",
            "assigned_to_name",
            "author_names",
            "published_at",
            "scheduled_for",
            "embargo_until",
            "revision_number",
            "word_count",
            "reading_time_minutes",
            "path",
            "updated_at",
            "created_at",
        ]

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.email if obj.assigned_to_id else None

    def get_author_names(self, obj):
        return list(obj.authors.values_list("display_name", flat=True))


class ContentEntrySerializer(serializers.ModelSerializer):
    revisions_count = serializers.SerializerMethodField()

    class Meta:
        model = ContentEntry
        fields = [
            "id",
            "organization",
            "publication",
            "content_type",
            "title",
            "slug",
            "locale",
            "status",
            "body",
            "custom_fields",
            "excerpt",
            "seo",
            "social",
            "authors",
            "terms",
            "featured_image",
            "created_by",
            "updated_by",
            "assigned_to",
            "editorial_team",
            "published_at",
            "unpublished_at",
            "embargo_until",
            "expires_at",
            "scheduled_for",
            "translation_group",
            "source_entry",
            "translation_status",
            "revision_number",
            "is_locked",
            "locked_by",
            "locked_at",
            "word_count",
            "reading_time_minutes",
            "related_entries",
            "series",
            "series_order",
            "collection",
            "channels",
            "metadata",
            "canonical_url",
            "path",
            "revisions_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "created_by",
            "updated_by",
            "revision_number",
            "published_at",
            "unpublished_at",
            "word_count",
            "reading_time_minutes",
            "created_at",
            "updated_at",
        ]

    def get_revisions_count(self, obj):
        return obj.revisions.count()

    def validate(self, attrs):
        content_type = attrs.get("content_type") or getattr(self.instance, "content_type", None)
        custom_fields = attrs.get("custom_fields")
        body = attrs.get("body")
        if content_type or custom_fields is not None:
            errors = validate_custom_fields(content_type, custom_fields)
            if errors:
                raise serializers.ValidationError({"custom_fields": errors})
        if body is not None:
            body_errors = validate_entry_body(body)
            if body_errors:
                raise serializers.ValidationError({"body": body_errors})
        return attrs


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class TopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Topic
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class NavigationMenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavigationMenu
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class LandingPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandingPage
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]
