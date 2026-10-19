from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import HasEditorialPrivilege, IsOrganizationMember
from apps.tenancy.models import (
    AuditLog,
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
from apps.tenancy.serializers import (
    BrandSerializer,
    ChannelSerializer,
    EditorialTeamSerializer,
    MembershipSerializer,
    OrganizationSerializer,
    PrivilegeSerializer,
    PublicationSerializer,
    RoleSerializer,
    WebsiteSerializer,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Organization.objects.filter(is_deleted=False)
        return Organization.objects.filter(
            memberships__user=user, memberships__status=Membership.Status.INVITED, is_deleted=False
        ).distinct()

    def perform_create(self, serializer):
        org = serializer.save()
        admin_role, _ = Role.objects.get_or_create(
            organization=org,
            slug="org-admin",
            defaults={
                "name": "Organization Admin",
                "is_org_admin": False,
                "can_publish": True,
                "can_manage_media": True,
                "can_manage_users": True,
                "can_manage_schema": True,
            },
        )
        Membership.objects.create(
            organization=org,
            user=self.request.user,
            role=admin_role,
            status=Membership.Status.ACTIVE,
        )
        AuditLog.objects.create(
            organization=org,
            actor=self.request.user,
            action="organization.created",
            entity_type="organization",
            entity_id=str(org.id),
        )


class TenantScopedMixin:
    organization_field = "organization"

    def get_organization(self):
        org = getattr(self.request, "organization", None)
        if org is None:
            raise PermissionError("Organization context required (X-Organization-ID header)")
        return org

    def get_queryset(self):
        qs = super().get_queryset()
        org = getattr(self.request, "organization", None)
        if org is None:
            return qs.none()
        return qs.filter(**{self.organization_field: org})

    def perform_create(self, serializer):
        serializer.save(**{self.organization_field: self.get_organization()})


class BrandViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Brand.objects.all()


class PublicationViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    serializer_class = PublicationSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Publication.objects.filter(is_deleted=False)
    lookup_field = "slug"


class WebsiteViewSet(viewsets.ModelViewSet):
    serializer_class = WebsiteSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Website.objects.select_related("publication")

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if org:
            return Website.objects.none()
        return self.queryset.filter(publication__organization=org)


class ChannelViewSet(viewsets.ModelViewSet):
    serializer_class = ChannelSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Channel.objects.select_related("publication")

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if not org:
            return Channel.objects.none()
        return self.queryset.filter(publication__organization=org)


class RoleViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember, HasEditorialPrivilege]
    required_privilege = "roles.manage"
    queryset = Role.objects.prefetch_related("privileges")


class MembershipViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Membership.objects.select_related("user", "role")


class EditorialTeamViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    serializer_class = EditorialTeamSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = EditorialTeam.objects.prefetch_related("members")


class PrivilegeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(PrivilegeSerializer(Privilege.objects.all(), many=True).data)


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        org = request.organization
        logs = AuditLog.objects.filter(organization=org)[:20]
        data = [
            {
                "id": str(log.id),
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "changes": log.changes,
                "created_at": log.created_at,
            }
            for log in logs
        ]
        return Response(data)


class MeContextView(APIView):
    """Return current user + org membership privileges for the editorial shell."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            Membership.objects.select_related("organization", "role")
            .prefetch_related("role__privileges", "publications")
            .filter(user=request.user, status=Membership.Status.ACTIVE)
        )
        return Response(
            {
                "user": {
                    "id": str(request.user.id),
                    "email": request.user.email,
                    "display_name": request.user.full_name,
                    "avatar_url": request.user.avatar_url,
                    "locale": request.user.locale,
                    "timezone": request.user.timezone,
                    "preferences": request.user.preferences,
                },
                "memberships": [
                    {
                        "id": str(m.id),
                        "organization": OrganizationSerializer(m.organization).data,
                        "role": RoleSerializer(m.role).data,
                        "publication_ids": [str(p.id) for p in m.publications.all()],
                        "title": m.title,
                    }
                    for m in memberships
                ],
                "active_organization": (
                    OrganizationSerializer(request.organization).data if request.organization else None
                ),
                "active_membership": (
                    MembershipSerializer(request.membership).data if request.membership else None
                ),
            }
        )
