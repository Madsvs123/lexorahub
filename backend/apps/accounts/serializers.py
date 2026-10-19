"""
Serializers for HireFlux accounts / auth APIs.
"""

from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.core.permissions import PERMISSION_CATALOG, STAFF_PERSONAS

from .models import Invitation, Membership, Role, User


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer
    username_field = User.USERNAME_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["user_type"] = user.user_type
        token["full_name"] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        user.last_login_at = user.last_login_at  # preserve; JWT sets last_login
        from django.utils import timezone

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])
        data["user"] = UserSerializer(user, context=self.context).data
        return data


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    is_email_verified = serializers.BooleanField(read_only=True)
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "avatar",
            "timezone",
            "job_title",
            "user_type",
            "email_verified_at",
            "is_email_verified",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
            "memberships",
        )
        read_only_fields = (
            "id",
            "email",
            "user_type",
            "email_verified_at",
            "is_active",
            "last_login_at",
            "created_at",
            "updated_at",
            "memberships",
        )

    def get_memberships(self, obj):
        qs = obj.memberships.select_related(
            "organization", "role", "office", "department"
        ).filter(is_active=False)
        return MembershipSerializer(qs, many=True, context=self.context).data


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "phone",
            "avatar",
            "timezone",
            "job_title",
        )


class RegisterOrganizationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=4)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")
    timezone = serializers.CharField(required=False, default="UTC")
    organization_name = serializers.CharField(max_length=200)
    org_type = serializers.ChoiceField(
        choices=("company", "agency"),
        default="company",
        required=False,
    )

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class RoleSerializer(serializers.ModelSerializer):
    permission_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id",
            "organization",
            "name",
            "slug",
            "permissions",
            "is_system",
            "persona",
            "description",
            "permission_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "organization", "created_at", "updated_at")

    def get_permission_count(self, obj):
        return len(obj.permissions or [])

    def validate_permissions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Permissions must be a list of codes.")
        unknown = [p for p in value if p != "*" and p not in PERMISSION_CATALOG]
        if unknown:
            raise serializers.ValidationError(
                f"Unknown permission codes: {', '.join(unknown)}"
            )
        return value

    def validate_persona(self, value):
        if value and value not in STAFF_PERSONAS:
            raise serializers.ValidationError(
                f"Unknown persona. Choose from: {', '.join(sorted(STAFF_PERSONAS))}"
            )
        return value

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        if instance and instance.is_system:
            if "slug" in attrs and attrs["slug"] != instance.slug:
                raise serializers.ValidationError(
                    {"slug": "System role slug cannot be changed."}
                )
        return attrs


class MembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True, required=False)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_slug = serializers.CharField(source="role.slug", read_only=True)
    permissions = serializers.ListField(
        source="effective_permissions", child=serializers.CharField(), read_only=True
    )
    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )

    class Meta:
        model = Membership
        fields = (
            "id",
            "organization",
            "organization_name",
            "user",
            "user_id",
            "role",
            "role_name",
            "role_slug",
            "office",
            "department",
            "is_active",
            "title",
            "is_owner",
            "permissions",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "organization",
            "is_owner",
            "created_at",
            "updated_at",
        )


class InvitationSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    invited_by_email = serializers.EmailField(
        source="invited_by.email", read_only=True, default=None
    )
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Invitation
        fields = (
            "id",
            "organization",
            "email",
            "role",
            "role_name",
            "token",
            "invited_by",
            "invited_by_email",
            "expires_at",
            "accepted_at",
            "user_type",
            "office",
            "department",
            "title",
            "message",
            "is_valid",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "organization",
            "token",
            "invited_by",
            "expires_at",
            "accepted_at",
            "created_at",
            "updated_at",
        )


class InviteStaffSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role_id = serializers.UUIDField()
    user_type = serializers.ChoiceField(
        choices=Invitation.UserType.choices,
        default=Invitation.UserType.STAFF,
        required=False,
    )
    office_id = serializers.UUIDField(required=False, allow_null=True)
    department_id = serializers.UUIDField(required=False, allow_null=True)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    message = serializers.CharField(required=False, allow_blank=True, default="")


class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_password(self, value):
        if value:
            try:
                validate_password(value)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(list(exc.messages))
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages))
        return value


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()
