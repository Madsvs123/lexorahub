import graphene
from graphene_django import DjangoObjectType

from apps.content.models import ContentEntry


class ContentEntryType(DjangoObjectType):
    class Meta:
        model = ContentEntry
        fields = (
            "id",
            "title",
            "slug",
            "locale",
            "status",
            "excerpt",
            "body",
            "custom_fields",
            "seo",
            "social",
            "published_at",
            "path",
            "word_count",
            "reading_time_minutes",
        )


class Query(graphene.ObjectType):
    entry = graphene.Field(
        ContentEntryType,
        id=graphene.UUID(),
        slug=graphene.String(),
        publication=graphene.UUID(),
        locale=graphene.String(default_value="en"),
    )
    entries = graphene.List(
        ContentEntryType,
        publication=graphene.UUID(required=True),
        locale=graphene.String(default_value="en"),
        limit=graphene.Int(default_value=20),
    )

    def resolve_entry(self, info, id=None, slug=None, publication=None, locale="en"):
        qs = ContentEntry.objects.filter(status=ContentEntry.Status.PUBLISHED, is_deleted=False)
        if publication:
            qs = qs.filter(publication_id=publication)
        if locale:
            qs = qs.filter(locale=locale)
        if id:
            return qs.filter(pk=id).first()
        if slug:
            return qs.filter(slug=slug).first()
        return None

    def resolve_entries(self, info, publication, locale="en", limit=20):
        return (
            ContentEntry.objects.filter(
                publication_id=publication,
                locale=locale,
                status=ContentEntry.Status.PUBLISHED,
                is_deleted=False,
            )
            .order_by("published_at")[:limit]
        )


schema = graphene.Schema(query=Query)
