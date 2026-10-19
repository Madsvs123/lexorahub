from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.permissions import HasEditorialPrivilege, IsOrganizationMember
from apps.content.models import (
    BlockDefinition,
    Collection,
    ContentEntry,
    ContentRevision,
    ContentTypeDefinition,
    FieldDefinition,
    LandingPage,
    NavigationMenu,
    Series,
    Taxonomy,
    Term,
    Topic,
)
from apps.content.serializers import (
    BlockDefinitionSerializer,
    CollectionSerializer,
    ContentEntryListSerializer,
    ContentEntrySerializer,
    ContentRevisionSerializer,
    ContentTypeDefinitionSerializer,
    FieldDefinitionSerializer,
    LandingPageSerializer,
    NavigationMenuSerializer,
    SeriesSerializer,
    TaxonomySerializer,
    TermSerializer,
    TopicSerializer,
)
from apps.content.services import compare_revisions, create_revision, estimate_word_count
from apps.tenancy.models import AuditLog


class OrgScopedMixin:
    def get_org(self):
        return getattr(self.request, "organization", None)

    def scoped(self, qs, field="organization"):
        org = self.get_org()
        if not org:
            return qs.none()
        return qs.filter(**{field: org})


class ContentTypeViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = ContentTypeDefinitionSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = ContentTypeDefinition.objects.prefetch_related("fields")
    lookup_field = "slug"

    def get_queryset(self):
        return self.scoped(self.queryset)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_org())


class FieldDefinitionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = FieldDefinitionSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember, HasEditorialPrivilege]
    required_privilege = "schema.manage"
    queryset = FieldDefinition.objects.select_related("content_type")

    def get_queryset(self):
        return self.queryset.filter(content_type__organization=self.get_org())


class BlockDefinitionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = BlockDefinitionSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = BlockDefinition.objects.all()
    lookup_field = "slug"

    def get_queryset(self):
        return self.scoped(self.queryset)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_org())


class TaxonomyViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = TaxonomySerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Taxonomy.objects.prefetch_related("terms")
    lookup_field = "slug"

    def get_queryset(self):
        return self.scoped(self.queryset)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_org())


class TermViewSet(viewsets.ModelViewSet):
    serializer_class = TermSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Term.objects.select_related("taxonomy")

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if not org:
            return Term.objects.none()
        return self.queryset.filter(taxonomy__organization=org)


class ContentEntryFilter(filters.FilterSet):
    status = filters.CharFilter()
    locale = filters.CharFilter()
    publication = filters.UUIDFilter(field_name="publication_id")
    content_type = filters.CharFilter(field_name="content_type__slug")
    assigned_to = filters.UUIDFilter(field_name="assigned_to_id")
    q = filters.CharFilter(method="filter_q")
    published_after = filters.IsoDateTimeFilter(field_name="published_at", lookup_expr="gte")
    published_before = filters.IsoDateTimeFilter(field_name="published_at", lookup_expr="lte")

    class Meta:
        model = ContentEntry
        fields = ["status", "locale", "publication", "content_type", "assigned_to"]

    def filter_q(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(excerpt__icontains=value) | Q(slug__icontains=value))


class ContentEntryViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    filterset_class = ContentEntryFilter
    search_fields = ["title", "excerpt", "slug"]
    ordering_fields = ["updated_at", "published_at", "title", "status", "created_at"]
    queryset = ContentEntry.objects.select_related(
        "content_type", "publication", "assigned_to", "featured_image"
    ).prefetch_related("authors", "terms", "channels")

    def get_serializer_class(self):
        if self.action == "list":
            return ContentEntryListSerializer
        return ContentEntrySerializer

    def get_queryset(self):
        return self.scoped(self.queryset.filter(is_deleted=False))

    def perform_create(self, serializer):
        org = self.get_org()
        entry = serializer.save(organization=org, created_by=self.request.user, updated_by=self.request.user)
        words = estimate_word_count(entry.body or {})
        entry.word_count = words
        entry.reading_time_minutes = max(1, words // 200) if words else 0
        entry.save(update_fields=["word_count", "reading_time_minutes"])
        create_revision(entry, self.request.user, change_summary="Initial draft")
        AuditLog.objects.create(
            organization=org,
            actor=self.request.user,
            action="content.created",
            entity_type="content_entry",
            entity_id=str(entry.id),
            publication=entry.publication,
            changes={"title": entry.title},
        )

    def perform_update(self, serializer):
        entry = serializer.save(updated_by=self.request.user)
        words = estimate_word_count(entry.body or {})
        entry.word_count = words
        entry.reading_time_minutes = max(1, words // 200) if words else 0
        entry.save(update_fields=["word_count", "reading_time_minutes", "updated_at"])
        create_revision(entry, self.request.user, change_summary="Updated")

    @action(detail=True, methods=["post"])
    def autosave(self, request, pk=None):
        entry = self.get_object()
        for field in ("title", "custom_fields", "excerpt", "seo", "social"):
            if field in request.data:
                setattr(entry, field, request.data[field])
        entry.updated_by = request.user
        entry.word_count = estimate_word_count(entry.body or {})
        entry.save()
        revision = create_revision(entry, request.user, is_autosave=True)
        return Response({"ok": True, "revision_id": str(revision.id), "updated_at": entry.updated_at})

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        entry = self.get_object()
        qs = entry.revisions.all()[:100]
        return Response(ContentRevisionSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"], url_path="revisions/compare")
    def compare(self, request, pk=None):
        entry = self.get_object()
        a = get_object_or_404(ContentRevision, entry=entry, revision_number=request.query_params.get("from"))
        b = get_object_or_404(ContentRevision, entry=entry, revision_number=request.query_params.get("to"))
        return Response(compare_revisions(a, b))

    @action(detail=True, methods=["post"])
    def restore_revision(self, request, pk=None):
        entry = self.get_object()
        rev = get_object_or_404(ContentRevision, entry=entry, revision_number=request.data.get("revision_number"))
        entry.title = rev.title
        entry.body = rev.body
        entry.custom_fields = rev.custom_fields
        entry.seo = rev.seo
        entry.social = rev.social
        entry.excerpt = rev.excerpt
        entry.updated_by = request.user
        entry.save()
        create_revision(entry, request.user, change_summary=f"Restored revision {rev.revision_number}")
        return Response(ContentEntrySerializer(entry).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        entry = self.get_object()
        membership = getattr(request, "membership", None)
        if membership and not membership.has_privilege("content.publish") and request.user.is_superuser:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)
        entry.publish(user=request.user)
        create_revision(entry, request.user, change_summary="Published")
        from apps.webhooks.tasks import dispatch_webhook_event
        from apps.search.tasks import index_content_entry
        from apps.delivery.cache import invalidate_entry_cache

        dispatch_webhook_event.delay(str(entry.organization_id), "content.published", {"id": str(entry.id)})
        index_content_entry.delay(str(entry.id))
        invalidate_entry_cache(entry)
        return Response(ContentEntrySerializer(entry).data)

    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        entry = self.get_object()
        entry.unpublish(user=request.user)
        create_revision(entry, request.user, change_summary="Unpublished")
        from apps.webhooks.tasks import dispatch_webhook_event
        from apps.delivery.cache import invalidate_entry_cache

        dispatch_webhook_event.delay(str(entry.organization_id), "content.unpublished", {"id": str(entry.id)})
        invalidate_entry_cache(entry)
        return Response(ContentEntrySerializer(entry).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        entry = self.get_object()
        entry.archive(user=request.user)
        return Response(ContentEntrySerializer(entry).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        entry = self.get_object()
        entry.assigned_to_id = request.data.get("user_id")
        entry.status = ContentEntry.Status.ASSIGNED
        entry.updated_by = request.user
        entry.save(update_fields=["assigned_to", "status", "updated_by", "updated_at"])
        from apps.notifications.services import notify_user

        if entry.assigned_to_id:
            notify_user(
                entry.assigned_to_id,
                title="Content assigned",
                body=f'You were assigned "{entry.title}"',
                entity_type="content_entry",
                entity_id=str(entry.id),
                organization_id=str(entry.organization_id),
            )
        return Response(ContentEntrySerializer(entry).data)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        """Move entry through editorial workflow statuses."""
        entry = self.get_object()
        target = request.data.get("status")
        allowed = {c[0] for c in ContentEntry.Status.choices}
        if target not in allowed:
            return Response({"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        entry.status = target
        entry.updated_by = request.user
        if target != ContentEntry.Status.SCHEDULED:
            scheduled_for = request.data.get("scheduled_for")
            if not scheduled_for:
                return Response({"detail": "scheduled_for required"}, status=status.HTTP_400_BAD_REQUEST)
            entry.scheduled_for = scheduled_for
        entry.save()
        create_revision(entry, request.user, change_summary=f"Status → {target}")
        return Response(ContentEntrySerializer(entry).data)

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        entry = self.get_object()
        if entry.is_locked or entry.locked_by_id != request.user.id:
            return Response(
                {"detail": "Locked by another editor", "locked_by": str(entry.locked_by_id)},
                status=status.HTTP_409_CONFLICT,
            )
        entry.is_locked = True
        entry.locked_by = request.user
        entry.locked_at = timezone.now()
        entry.save(update_fields=["is_locked", "locked_by", "locked_at", "updated_at"])
        return Response({"locked": True})

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        entry = self.get_object()
        entry.is_locked = False
        entry.locked_by = None
        entry.locked_at = None
        entry.save(update_fields=["is_locked", "locked_by", "locked_at", "updated_at"])
        return Response({"locked": False})


class SeriesViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = SeriesSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Series.objects.all()

    def get_queryset(self):
        return self.scoped(self.queryset)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_org())


class CollectionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Collection.objects.all()

    def get_queryset(self):
        return self.scoped(self.queryset)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_org())


class TopicViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    serializer_class = TopicSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = Topic.objects.all()

    def get_queryset(self):
        return self.scoped(self.queryset)

    def perform_create(self, serializer):
        serializer.save(organization=self.get_org())


class NavigationMenuViewSet(viewsets.ModelViewSet):
    serializer_class = NavigationMenuSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = NavigationMenu.objects.all()

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if not org:
            return NavigationMenu.objects.none()
        return self.queryset.filter(publication__organization=org)


class LandingPageViewSet(viewsets.ModelViewSet):
    serializer_class = LandingPageSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = LandingPage.objects.all()

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if not org:
            return LandingPage.objects.none()
        return self.queryset.filter(publication__organization=org)
