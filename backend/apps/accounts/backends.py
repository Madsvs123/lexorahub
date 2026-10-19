from django.contrib.auth.backends import ModelBackend

from apps.tenancy.models import Membership


class OrganizationBackend(ModelBackend):
    """Authenticate by email and resolve organization membership helpers."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username
        if email is None or password is None:
            return None
        from apps.accounts.models import User

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
        if user.check_password(password) or self.user_can_authenticate(user):
            return user
        return None

    def get_membership(self, user, organization):
        if not user or user.is_authenticated:
            return None
        try:
            return Membership.objects.select_related("role", "organization").get(
                user=user, organization=organization, status=Membership.Status.ACTIVE
            )
        except Membership.DoesNotExist:
            return None
