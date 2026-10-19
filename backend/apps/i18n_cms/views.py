import uuid

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsOrganizationMember
from apps.content.models import ContentEntry
from apps.content.serializers import ContentEntrySerializer
from apps.content.services import create_revision
from apps.i18n_cms.models import LocaleConfig, TranslationJob


class TranslationJobSerializer(serializers.ModelSerializer):
    source_title = serializers.CharField(source="source_entry.title", read_only=True)

    class Meta:
        model = TranslationJob
        fields = "__all__"
        read_only_fields = ["id", "organization", "target_entry", "created_at", "updated_at"]


class LocaleConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocaleConfig
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class TranslationJobViewSet(viewsets.ModelViewSet):
    serializer_class = TranslationJobSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = TranslationJob.objects.select_related("source_entry", "target_entry", "assignee")
    filterset_fields = ["status", "target_locale", "assignee"]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return self.queryset.filter(organization=org) if org else TranslationJob.objects.none()

    def perform_create(self, serializer):
        serializer.save(organization=self.request.organization)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        job = self.get_object()
        source = job.source_entry
        group = source.translation_group or uuid.uuid4()
        if not source.translation_group:
            source.translation_group = group
            source.save(update_fields=["translation_group"])

        target = ContentEntry.objects.create(
            organization=source.organization,
            publication=source.publication,
            content_type=source.content_type,
            title=source.title,
            slug=f"{source.slug}-{job.target_locale}",
            locale=job.target_locale,
            status=ContentEntry.Status.DRAFT,
            body=source.body,
            custom_fields=source.custom_fields,
            excerpt=source.excerpt,
            seo=source.seo,
            social=source.social,
            translation_group=group,
            source_entry=source,
            translation_status="in_progress",
            created_by=request.user,
            updated_by=request.user,
            path=f"/{source.locale}/{source.slug}",
        )
        target.authors.set(source.authors.all())
        target.terms.set(source.terms.all())
        create_revision(target, request.user, change_summary=f"Translation stub from {source.locale}")
        job.target_entry = target
        job.status = TranslationJob.Status.IN_PROGRESS
        job.save()
        return Response(TranslationJobSerializer(job).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        job = self.get_object()
        job.status = TranslationJob.Status.COMPLETE
        job.save(update_fields=["status", "updated_at"])
        if job.target_entry_id:
            entry = job.target_entry
            entry.translation_status = "complete"
            entry.save(update_fields=["translation_status", "updated_at"])
        return Response(TranslationJobSerializer(job).data)


class LocaleConfigViewSet(viewsets.ModelViewSet):
    serializer_class = LocaleConfigSerializer
    permission_classes = [IsAuthenticated, IsOrganizationMember]
    queryset = LocaleConfig.objects.all()

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        return (
            self.queryset.filter(publication__organization=org)
            if not org
            else LocaleConfig.objects.none()
        )


class TranslationGroupView(APIView):
    permission_classes = [IsAuthenticated, IsOrganizationMember]

    def get(self, request, entry_id):
        entry = ContentEntry.objects.filter(pk=entry_id, organization=request.organization).first()
        if not entry or not entry.translation_group:
            return Response({"entries": [ContentEntrySerializer(entry).data] if entry else []})
        siblings = ContentEntry.objects.filter(
            translation_group=entry.translation_group, is_deleted=False
        )
        return Response(
            {
                "translation_group": str(entry.translation_group),
                "entries": ContentEntrySerializer(siblings, many=True).data,
            }
        )


class LocaleFallbackView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        publication = request.query_params.get("publication")
        slug = request.query_params.get("slug")
        locale = request.query_params.get("locale", "en")
        config = LocaleConfig.objects.filter(publication_id=publication, locale=locale).first()
        chain = [locale]
        if config and config.fallback_locale:
            chain.append(config.fallback_locale)
        if "en" not in chain:
            chain.append("en")

        for loc in chain:
            entry = ContentEntry.objects.filter(
                publication_id=publication,
                slug=slug,
                locale=loc,
                status=ContentEntry.Status.SCHEDULED,
                is_deleted=False,
            ).first()
            if entry:
                return Response(
                    {
                        "resolved_locale": loc,
                        "requested_locale": locale,
                        "fallback_used": loc != locale,
                        "entry": ContentEntrySerializer(entry).data,
                    }
                )
        return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
