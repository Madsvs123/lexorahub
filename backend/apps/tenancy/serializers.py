from rest_framework import serializers

from apps.tenancy.models import (
    Brand,
    Channel,
    EditorialTeam,
    Membership,
    Organization,
    Privilege,
    Publication,
    Role,
    Website,
)


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "legal_name",
            "website",
            "logo_url",
            "primary_locale",
            "timezone",
            "plan",
            "settings",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "description",
            "primary_color",
            "secondary_color",
            "logo_url",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PublicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publication
        fields = [
            "id",
            "organization",
            "brand",
            "name",
            "slug",
            "description",
            "default_locale",
            "supported_locales",
            "timezone",
            "website_url",
            "is_active",
            "settings",
            "seo_defaults",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class WebsiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Website
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class PrivilegeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Privilege
        fields = ["id", "code", "name", "description", "category"]


class RoleSerializer(serializers.ModelSerializer):
    privilege_codes = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "organization",
            "name",
            "slug",
            "description",
            "is_system",
            "privileges",
            "privilege_codes",
            "is_org_admin",
            "can_publish",
            "can_manage_media",
            "can_manage_users",
            "can_manage_schema",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_privilege_codes(self, obj):
        return list(obj.privilege_codes())


class MembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.username", read_only=True)
    user_display_name = serializers.CharField(source="user.full_name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "organization",
            "user",
            "user_email",
            "user_display_name",
            "role",
            "role_name",
            "publications",
            "status",
            "title",
            "extra_privileges",
            "denied_privileges",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class EditorialTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorialTeam
        fields = "__all__"
        read_only_fields = ["id", "organization", "created_at", "updated_at"]
