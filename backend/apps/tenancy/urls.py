from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tenancy.views import (
    AuditLogListView,
    BrandViewSet,
    ChannelViewSet,
    EditorialTeamViewSet,
    MeContextView,
    MembershipViewSet,
    OrganizationViewSet,
    PrivilegeListView,
    PublicationViewSet,
    RoleViewSet,
    WebsiteViewSet,
)

router = DefaultRouter()
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("brands", BrandViewSet, basename="brand")
router.register("publications", PublicationViewSet, basename="publication")
router.register("websites", WebsiteViewSet, basename="website")
router.register("channels", ChannelViewSet, basename="channel")
router.register("roles", RoleViewSet, basename="role")
router.register("memberships", MembershipViewSet, basename="membership")
router.register("teams", EditorialTeamViewSet, basename="team")

urlpatterns = [
    path("context/", MeContextView.as_view(), name="me-context"),
    path("privileges/", PrivilegeListView.as_view(), name="privileges"),
    path("audit-logs/", AuditLogListView.as_view(), name="audit-logs"),
    path("", include(router.urls)),
]
