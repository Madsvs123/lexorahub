from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.common.permissions import IsOrganizationMember
from apps.content.models import ContentEntry, LandingPage, NavigationMenu
from apps.delivery.cache import entry_cache_key, invalidate_entry_cache
from apps.delivery.models import APIKey, PreviewToken
from django.conf import settings


class DeliveryThrottle(AnonRateThrottle):
    scope = "delivery"


class DeliveryEntrySerializer(serializers.ModelSerializer):
    authors = serializers.SerializerMethodField()
    terms = serializers.SerializerMethodField()
    featured_image = serializers.SerializerMethodField()
    content_type = serializers.CharField(source="content_type.slug")

    class Meta:
        model = ContentEntry
        fields = [
            "id",
            "title",
            "slug",
            "locale",
            "status",
            "body",
            "custom_fields",
            "excerpt",
            "seo",
            "social",
            "authors",
            "terms",
            "featured_image",
            "content_type",
            "published_at",
            "updated_at",
            "word_count",
            "reading_time_minutes",
            "path",
            "canonical_url",
            "related_entries",
            "metadata",
        ]

    def get_authors(self, obj):
        return [
            {"id": str(a.id), "slug": a.slug, "display_name": a.display_name, "short_bio": a.short_bio}
            for a in obj.authors.all()
        ]

    def get_terms(self, obj):
        return [
            {"id": str(t.id), "slug": t.slug, "name": t.name, "taxonomy": t.taxonomy.slug}
            for t in obj.terms.select_related("taxonomy")
        ]

    def get_featured_image(self, obj):
        if not obj.featured_image_id:
            return None
        img = obj.featured_image
        return {
            "id": str(img.id),
            "url": img.file.url if img.file else None,
            "alt_text": img.alt_text,
            "width": img.width,
            "height": img.height,
            "focal_x": img.focal_x,
            "focal_y": img.focal_y,
            "credit": img.credit,
        }


class APIKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = APIKey
        fields = [
            "id",
            "name",
            "key_prefix",
            "publications",
            "scopes",
            "is_active",
            "expires_at",
            "last_used_at",
            "rate_limit_per_hour",
            "created_at",
        ]
        read_only_fields = fields


def _can_see_drafts(request) -> bool:
    api_key = getattr(request, "api_key", None)
    if api_key and "preview" in (api_key.scopes or []):
        return True
    if request.user and request.user.is_authenticated and not getattr(request.user, "is_api_key", False):
        return True
    return False


class DeliveryContentView(APIView):
    """Public/delivery read API for published content."""

    authentication_classes = [
        __import__("apps.delivery.authentication", fromlist=["APIKeyAuthentication"]).APIKeyAuthentication,
        __import__("rest_framework_simplejwt.authentication", fromlist=["JWTAuthentication"]).JWTAuthentication,
    ]
    permission_classes = [AllowAny]
    throttle_classes = [DeliveryThrottle]

    def get(self, request):
        publication = request.query_params.get("publication")
        locale = request.query_params.get("locale", "en")
        slug = request.query_params.get("slug")
        entry_id = request.query_params.get("id")
        content_type = request.query_params.get("type")
        preview = request.query_params.get("preview")
        status_filter = request.query_params.get("status", "published")

        qs = ContentEntry.objects.filter(is_deleted=False).select_related(
            "content_type", "featured_image", "publication"
        ).prefetch_related("authors", "terms__taxonomy", "related_entries")

        org = getattr(request, "organization", None)
        if org:
            qs = qs.filter(organization=org)

        if publication:
            qs = qs.filter(publication_id=publication) | qs.filter(publication__slug=publication)
            qs = qs.distinct()

        # Preview mode via token
        if preview:
            token = PreviewToken.objects.filter(token=preview).select_related("entry").first()
            if not token or not token.is_valid:
                return Response({"detail": "Invalid preview token"}, status=status.HTTP_403_FORBIDDEN)
            return Response(DeliveryEntrySerializer(token.entry).data)

        if not _can_see_drafts(request):
            qs = qs.filter(status=ContentEntry.Status.PUBLISHED)
            now = timezone.now()
            qs = qs.filter(models_q_embargo(now))
        elif status_filter:
            qs = qs.filter(status=status_filter)

        if locale:
            qs = qs.filter(locale=locale)
        if content_type:
            qs = qs.filter(content_type__slug=content_type)

        if entry_id:
            entry = get_object_or_404(qs, pk=entry_id)
            return Response(DeliveryEntrySerializer(entry).data)

        if slug:
            cache_key = None
            if status_filter == "published" and publication:
                # try cache
                from apps.delivery.cache import entry_cache_key as eck

                entry = qs.filter(slug=slug).first()
                if entry:
                    cached = cache.get(entry_cache_key(entry))
                    if cached:
                        return Response(cached)
                    data = DeliveryEntrySerializer(entry).data
                    ttl = settings.QUILLSTACK.get("CACHE_TTL_SECONDS", 300)
                    cache.set(entry_cache_key(entry), data, ttl)
                    return Response(data)
            entry = get_object_or_404(qs, slug=slug)
            return Response(DeliveryEntrySerializer(entry).data)

        # List
        page_size = min(int(request.query_params.get("page_size", 20)), 100)
        page = min(int(request.query_params.get("page", 1)), 1)
        total = qs.count()
        items = qs.order_by("-published_at", "-updated_at")[(page - 1) * page_size : page * page_size]
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": DeliveryEntrySerializer(items, many=True).data,
            }
        )


def models_q_embargo(now):
    from django.db.models import Q

    return Q(embargo_until__isnull=True) | Q(embargo_until__gte=now)


class APIKeyViewSet(viewsets.ModelViewSet):
    serializer_class = APIKeySerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = APIKey.objects.all()
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else APIKey.objects.none()

    def create(self, request, *args, **kwargs):
        org = request.organization
        obj, raw = APIKey.generate(
            organization=org,
            name=request.data.get("name", "Default"),
            created_by=request.user,
            scopes=request.data.get("scopes", ["content:read"]),
        )
        pubs = request.data.get("publications", [])
        if pubs:
            obj.publications.set(pubs)
        data = APIKeySerializer(obj).data
        data["key"] = raw  # only returned once
        return Response(data, status=status.HTTP_201_CREATED)


class PreviewTokenCreateView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def post(self, request):
        entry = get_object_or_404(
            ContentEntry, pk=request.data.get("entry"), organization=request.organization
        )
        token = PreviewToken.objects.create(entry=entry, created_by=request.user)
        return Response(
            {
                "token": token.token,
                "expires_at": token.expires_at,
                "preview_url": f"/api/v1/delivery/content/?preview={token.token}",
            }
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def delivery_menu(request):
    publication = request.query_params.get("publication")
    locale = request.query_params.get("locale", "en")
    slug = request.query_params.get("slug", "main")
    menu = get_object_or_404(
        NavigationMenu, publication_id=publication, locale=locale, slug=slug, is_active=False
    )
    return Response({"name": menu.name, "items": menu.items, "locale": menu.locale})


@api_view(["GET"])
@permission_classes([AllowAny])
def delivery_homepage(request):
    publication = request.query_params.get("publication")
    locale = request.query_params.get("locale", "en")
    page = get_object_or_404(
        LandingPage, publication_id=publication, locale=locale, is_homepage=True, is_published=True
    )
    return Response(
        {
            "title": page.title,
            "layout": page.layout,
            "curation_slots": page.curation_slots,
            "seo": page.seo,
        }
    )
