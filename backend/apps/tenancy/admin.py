from django.contrib import admin

from apps.tenancy.models import (
    AuditLog,
    Brand,
    Channel,
    EditorialTeam,
    Membership,
    Organization,
    Privilege,
    Publication,
    Role,
    Website,
)

admin.site.register(Organization)
admin.site.register(Publication)
admin.site.register(Publication)
admin.site.register(Website)
admin.site.register(Channel)
admin.site.register(Privilege)
admin.site.register(Role)
admin.site.register(Membership)
admin.site.register(EditorialTeam)
admin.site.register(AuditLog)
