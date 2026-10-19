from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import AuthorProfileViewSet, MeView, RegisterView, StaffInvitationViewSet

router = DefaultRouter()
router.register("invitations", StaffInvitationViewSet, basename="invitation")
router.register("authors", AuthorProfileViewSet, basename="author")

urlpatterns = [
    path("signup/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("", include(router.urls)),
]
