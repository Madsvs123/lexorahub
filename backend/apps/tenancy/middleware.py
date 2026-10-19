from apps.tenancy.models import Membership, Organization


class TenantMiddleware:
    """
    Resolve organization from X-Organization-ID / X-Organization-Slug headers
    and attach membership for the authenticated user.
    """

    HEADER_ID = "HTTP_X_ORGANIZATION_ID"
    HEADER_SLUG = "HTTP_X_ORGANIZATION_SLUG"
    HEADER_PUBLICATION = "HTTP_X_PUBLICATION_ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None
        request.membership = None
        request.publication_id = request.META.get(self.HEADER_PUBLICATION)

        org = None
        org_id = request.META.get(self.HEADER_ID)
        org_slug = request.META.get(self.HEADER_SLUG)

        if org_slug:
            org = Organization.objects.filter(slug=org_slug, is_active=True, is_deleted=False).first()
        elif org_id:
            org = Organization.objects.filter(pk=org_id, is_active=True, is_deleted=False).first()

        if org is not None:
            request.organization = org
            user = getattr(request, "user", None)
            if user is not None and user.is_authenticated:
                request.membership = (
                    Membership.objects.select_related("role")
                    .filter(user=user, organization=org)
                    .first()
                )

        return self.get_response(request)
