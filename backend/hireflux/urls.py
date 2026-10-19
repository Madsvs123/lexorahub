"""
URL configuration for HireFlux.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.organizations.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.jobs.urls")),
    path("api/v1/", include("apps.candidates.urls")),
    path("api/v1/", include("apps.pipelines.urls")),
    path("api/v1/", include("apps.screening.urls")),
    path("api/v1/", include("apps.interviews.urls")),
    path("api/v1/", include("apps.assessments.urls")),
    path("api/v1/", include("apps.offers.urls")),
    path("api/v1/", include("apps.talent.urls")),
    path("api/v1/", include("apps.comms.urls")),
    path("api/v1/", include("apps.portal.urls")),
    path("api/v1/", include("apps.analytics.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
