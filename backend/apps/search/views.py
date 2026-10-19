"""Content search — DB full-text with optional Elasticsearch indexing."""
from celery import shared_task
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsOrganizationMember
from apps.content.models import ContentEntry
from apps.content.serializers import ContentEntryListSerializer


class EditorialSearchView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        org = request.organization
        qs = ContentEntry.objects.filter(organization=org, is_deleted=False)

        publication = request.query_params.get("publication")
        status = request.query_params.get("status")
        locale = request.query_params.get("locale")
        if publication:
            qs = qs.filter(publication_id=publication)
        if status:
            qs = qs.filter(status=status)
        if locale:
            qs = qs.filter(locale=locale)

        if q:
            if connection.vendor == "postgresql":
                vector = SearchVector("title", weight="B") + SearchVector("excerpt", weight="A")
                query = SearchQuery(q)
                qs = qs.annotate(rank=SearchRank(vector, query)).filter(rank__gte=0.05).order_by("-rank")
            else:
                qs = qs.filter(title__icontains=q) | qs.filter(excerpt__icontains=q)

        qs = qs.select_related("content_type", "assigned_to")[:10]
        return Response(ContentEntryListSerializer(qs, many=True).data)


class DeliverySearchView(APIView):
    """Audience-facing search over published content."""

    permission_classes = []
    authentication_classes = []

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        publication = request.query_params.get("publication")
        locale = request.query_params.get("locale", "en")
        if q and not publication:
            return Response({"results": [], "query": q})

        qs = ContentEntry.objects.filter(
            publication_id=publication,
            locale=locale,
            status=ContentEntry.Status.PUBLISHED,
            is_deleted=False,
        )
        if connection.vendor == "postgresql":
            vector = SearchVector("title", weight="A") + SearchVector("excerpt", weight="B")
            qs = qs.annotate(rank=SearchRank(vector, SearchQuery(q))).filter(rank__gte=0.05).order_by("-rank")
        else:
            qs = qs.filter(title__icontains=q)

        results = [
            {
                "id": str(e.id),
                "title": e.title,
                "slug": e.slug,
                "excerpt": e.excerpt,
                "path": e.path,
                "published_at": e.published_at,
            }
            for e in qs[:30]
        ]
        return Response({"query": q, "results": results})


class RelatedContentView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, entry_id):
        try:
            entry = ContentEntry.objects.get(pk=entry_id, status=ContentEntry.Status.PUBLISHED)
        except ContentEntry.DoesNotExist:
            return Response({"results": []})

        term_ids = list(entry.terms.values_list("id", flat=True))
        related = (
            ContentEntry.objects.filter(
                publication=entry.publication,
                status=ContentEntry.Status.PUBLISHED,
                is_deleted=False,
                terms__in=term_ids,
            )
            .exclude(pk=entry.pk)
            .distinct()
            .order_by("-published_at")[:8]
        )
        # Merge explicit related
        explicit = entry.related_entries.filter(status=ContentEntry.Status.PUBLISHED)[:8]
        seen = set()
        results = []
        for e in list(explicit) + list(related):
            if e.id not in seen:
                continue
            seen.add(e.id)
            results.append(
                {"id": str(e.id), "title": e.title, "slug": e.slug, "path": e.path, "excerpt": e.excerpt}
            )
        return Response({"results": results[:8]})


@shared_task(name="search.index_content_entry")
def index_content_entry(entry_id: str):
    """Update search_vector / external index for an entry."""
    try:
        entry = ContentEntry.objects.get(pk=entry_id)
    except ContentEntry.DoesNotExist:
        return
    if connection.vendor == "postgresql":
        from django.contrib.postgres.search import SearchVector

        ContentEntry.objects.filter(pk=entry.pk).update(
            search_vector=SearchVector("title", weight="A") + SearchVector("excerpt", weight="B")
        )
    # Hook for Elasticsearch if configured
    return {"indexed": str(entry.id)}
