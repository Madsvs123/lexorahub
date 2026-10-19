from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("django-admin/", admin.site.urls),
    # Auth
    path("api/v1/auth/token/", TokenRefreshView.as_view(), name="token_obtain"),
    path("api/v1/auth/token/refresh/", TokenObtainPairView.as_view(), name="token_refresh"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    # Core platform
    path("api/v1/tenancy/", include("apps.tenancy.urls")),
    path("api/v1/content/", include("apps.content.urls")),
    path("api/v1/editorial/", include("apps.editorial.urls")),
    path("api/v1/media/", include("apps.media_library.urls")),
    path("api/v1/scheduling/", include("apps.scheduling.urls")),
    path("api/v1/i18n/", include("apps.i18n_cms.urls")),
    path("api/v1/search/", include("apps.search.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/webhooks/", include("apps.webhooks.urls")),
    path("api/v1/collaboration/", include("apps.collaboration.urls")),
    # Public delivery API
    path("api/v1/delivery/", include("apps.delivery.urls")),
    # Schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
    # GraphQL
    path("graphql/", include("apps.delivery.graphql_urls")),
]
