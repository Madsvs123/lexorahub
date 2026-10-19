from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.content.models import (
    BlockDefinition,
    ContentTypeDefinition,
    FieldDefinition,
    Taxonomy,
    Term,
)
from apps.content.services import SYSTEM_BLOCKS
from apps.tenancy.models import (
    Brand,
    Channel,
    Membership,
    Organization,
    Privilege,
    Publication,
    Role,
    Website,
)


class Command(BaseCommand):
    help = "Seed a demo QuillStack organization, publication, roles, and Article content type"

    def handle(self, *args, **options):
        User = get_user_model()
        admin, created = User.objects.get_or_create(
            email="editor@quillstack.local",
            defaults={
                "display_name": "Desk Editor",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            admin.set_password("quillstack")
            admin.save()
            self.stdout.write("Created editor@quillstack.local / quillstack")

        org, _ = Organization.objects.get_or_create(
            slug="acme-media",
            defaults={
                "name": "Acme Media Group",
                "primary_locale": "en",
                "timezone": "UTC",
            },
        )
        brand, _ = Brand.objects.get_or_create(
            organization=org, slug="acme-daily", defaults={"name": "Acme Daily"}
        )
        pub, _ = Publication.objects.get_or_create(
            organization=org,
            slug="acme-daily",
            defaults={
                "name": "Acme Daily",
                "brand": brand,
                "default_locale": "en",
                "supported_locales": ["en", "es", "fr"],
                "website_url": "https://example.com",
            },
        )
        Website.objects.get_or_create(
            publication=pub,
            slug="main",
            defaults={"name": "Main Site", "domain": "example.com", "is_primary": False},
        )
        Channel.objects.get_or_create(
            publication=pub, slug="web", defaults={"name": "Web", "channel_type": "web"}
        )
        Channel.objects.get_or_create(
            publication=pub,
            slug="newsletter",
            defaults={"name": "Newsletter", "channel_type": "newsletter"},
        )

        role, _ = Role.objects.get_or_create(
            organization=org,
            slug="editor-in-chief",
            defaults={
                "name": "Editor in Chief",
                "is_org_admin": True,
                "can_publish": True,
                "can_manage_media": True,
                "can_manage_users": True,
                "can_manage_schema": True,
            },
        )
        role.privileges.set(Privilege.objects.all())
        Membership.objects.get_or_create(
            organization=org,
            user=admin,
            defaults={"role": role, "status": Membership.Status.INVITED},
        )

        article, _ = ContentTypeDefinition.objects.get_or_create(
            organization=org,
            slug="article",
            defaults={
                "name": "Article",
                "publication": pub,
                "description": "Standard news/magazine article",
                "is_translatable": True,
                "workflow_enabled": True,
            },
        )
        defaults_fields = [
            ("dek", "Dek", "text", True),
            ("kicker", "Kicker", "text", False),
            ("source", "Source", "text", False),
            ("is_breaking", "Breaking", "boolean", False),
        ]
        for i, (key, name, ftype, required) in enumerate(defaults_fields):
            FieldDefinition.objects.get_or_create(
                content_type=article,
                api_key=key,
                defaults={
                    "name": name,
                    "field_type": ftype,
                    "is_required": required,
                    "sort_order": i,
                    "is_listable": True,
                },
            )

        for block in SYSTEM_BLOCKS:
            BlockDefinition.objects.get_or_create(
                organization=org,
                slug=block["slug"],
                defaults={
                    "name": block["name"],
                    "schema": block["schema"],
                    "is_system": True,
                },
            )

        cats, _ = Taxonomy.objects.get_or_create(
            organization=org,
            slug="categories",
            defaults={"name": "Categories", "publication": pub, "is_hierarchical": True},
        )
        tags, _ = Taxonomy.objects.get_or_create(
            organization=org,
            slug="tags",
            defaults={
                "name": "Tags",
                "publication": pub,
                "is_hierarchical": False,
                "is_tag_like": True,
            },
        )
        for name in ["Politics", "Business", "Culture", "Technology", "Sports"]:
            Term.objects.get_or_create(taxonomy=cats, slug=name.lower(), defaults={"name": name})
        for name in ["Investigation", "Feature", "Opinion", "Brief"]:
            Term.objects.get_or_create(taxonomy=tags, slug=name.lower(), defaults={"name": name})

        self.stdout.write(self.style.SUCCESS(f"Seeded org={org.slug} publication={pub.slug}"))
