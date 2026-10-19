from django.db.models.signals import post_migrate
from django.dispatch import receiver

from apps.tenancy.models import DEFAULT_PRIVILEGES, Privilege


@receiver(post_migrate)
def seed_privileges(sender, **kwargs):
    if sender.name != "apps.tenancy":
        return
    for code, name, category in DEFAULT_PRIVILEGES:
        Privilege.objects.update_or_create(
            code=code, defaults={"name": name, "category": category}
        )
