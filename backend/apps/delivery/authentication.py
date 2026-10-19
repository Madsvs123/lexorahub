from django.utils import timezone
from rest_framework import authentication, exceptions

from apps.delivery.models import APIKey


class APIKeyAuthentication(authentication.BaseAuthentication):
    header = "HTTP_X_API_KEY"
    keyword = "Api-Key"

    def authenticate(self, request):
        raw = request.META.get(self.header)
        if not raw:
            auth = authentication.get_authorization_header(request).decode()
            if auth.startswith(self.keyword):
                raw = auth[len(self.keyword) :].strip()
        if not raw:
            return None

        prefix = raw[:12]
        candidates = APIKey.objects.filter(key_prefix=prefix, is_active=True).select_related("organization")
        for key in candidates:
            if key.matches(raw):
                key.last_used_at = timezone.now()
                key.save(update_fields=["last_used_at"])
                request.organization = key.organization
                request.api_key = key
                # Attach a lightweight principal
                return (APIKeyUser(key), raw)
        raise exceptions.AuthenticationFailed("Invalid API key")


class APIKeyUser:
    is_authenticated = True
    is_anonymous = False
    is_api_key = True

    def __init__(self, api_key: APIKey):
        self.api_key = api_key
        self.pk = api_key.id
        self.id = api_key.id

    def __str__(self):
        return f"APIKey:{self.api_key.name}"
