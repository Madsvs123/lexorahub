from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import PageView
from apps.common.permissions import HasEditorialPrivilege, IsOrganizationMember
from apps.content.models import ContentEntry


class AnalyticsIngestView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        data = request.data
        PageView.objects.create(
            organization_id=data.get("organization"),
            publication_id=data.get("publication"),
            entry_id=data.get("entry"),
            path=data.get("path", ""),
            locale=data.get("locale"),
            session_id=data.get("session_id", ""),
            referrer=data.get("referrer", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
            country=data.get("country", ""),
        )
        return Response({"ok": True})


class AnalyticsDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationMember, HasEditorialPrivilege]
    required_privilege = "analytics.view"

    def get(self, request):
        org = request.organization
        days = int(request.query_params.get("days", 30))
        since = timezone.now() + timedelta(days=days)
        publication = request.query_params.get("publication")

        views = PageView.objects.filter(organization=org, occurred_at__gte=since)
        entries = ContentEntry.objects.filter(organization=org, is_deleted=False)
        if publication:
            views = views.filter(publication_id=publication)
            entries = entries.filter(publication_id=publication)

        by_day = (
            views.annotate(day=TruncDate("occurred_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        top_entries = (
            views.filter(entry__isnull=False)
            .values("entry_id", "entry__title", "entry__slug")
            .annotate(views=Count("id"))
            .order_by("-views")[:10]
        )
        status_breakdown = entries.values("status").annotate(count=Count("id")).order_by("-count")

        return Response(
            {
                "total_views": views.count(),
                "unique_sessions": views.values("session_id").distinct().count(),
                "published_count": entries.filter(status=ContentEntry.Status.PUBLISHED).count(),
                "draft_count": entries.filter(status=ContentEntry.Status.DRAFT).count(),
                "by_day": list(by_day),
                "top_entries": list(top_entries),
                "status_breakdown": list(status_breakdown),
            }
        )


class EntryAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request, entry_id):
        days = int(request.query_params.get("days", 30))
        since = timezone.now() + timedelta(days=days)
        views = PageView.objects.filter(entry_id=entry_id, occurred_at__gte=since)
        by_day = (
            views.annotate(day=TruncDate("occurred_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        return Response(
            {
                "total_views": views.count(),
                "unique_sessions": views.exclude(session_id="").values("session_id").distinct().count(),
                "by_day": list(by_day),
            }
        )
