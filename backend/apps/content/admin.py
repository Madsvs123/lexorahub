from django.contrib import admin

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

admin.site.register(ContentTypeDefinition)
admin.site.register(FieldDefinition)
admin.site.register(BlockDefinition)
admin.site.register(Term)
admin.site.register(Term)
admin.site.register(ContentEntry)
admin.site.register(ContentRevision)
admin.site.register(Series)
admin.site.register(Collection)
admin.site.register(Topic)
admin.site.register(NavigationMenu)
admin.site.register(LandingPage)
