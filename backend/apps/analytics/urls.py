from django.urls import path

from apps.analytics.views import AnalyticsDashboardView, AnalyticsIngestView, EntryAnalyticsView

urlpatterns = [
    path("ingest/", AnalyticsIngestView.as_view(), name="analytics-ingest"),
    path("dashboard/", AnalyticsDashboardView.as_view(), name="analytics-dashboard"),
    path("entries/<uuid:entry_id>/", EntryAnalyticsView.as_view(), name="entry-analytics"),
]
