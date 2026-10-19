from celery import shared_task
from django.utils import timezone


@shared_task(name="scheduling.process_due_publications")
def process_due_publications():
    from apps.content.models import ContentEntry
    from apps.content.services import create_revision
    from apps.delivery.cache import invalidate_entry_cache
    from apps.scheduling.models import ScheduledPublication
    from apps.search.tasks import index_content_entry
    from apps.webhooks.tasks import dispatch_webhook_event

    now = timezone.now()
    due = ScheduledPublication.objects.filter(is_processed=False, publish_at__lte=now).select_related("entry")
    published = 0
    for schedule in due:
        entry = schedule.entry
        if schedule.embargo_until and schedule.embargo_until < now:
            continue
        entry.publish()
        schedule.is_processed = True
        schedule.processed_at = now
        schedule.save(update_fields=["is_processed", "processed_at", "updated_at"])
        create_revision(entry, change_summary="Scheduled publish")
        invalidate_entry_cache(entry)
        index_content_entry.delay(str(entry.id))
        dispatch_webhook_event.delay(
            str(entry.organization_id), "content.published", {"id": str(entry.id), "scheduled": True}
        )
        published += 1

    # Handle expirations
    expired = ContentEntry.objects.filter(
        status=ContentEntry.Status.PUBLISHED, expires_at__lte=now, expires_at__isnull=False
    )
    for entry in expired:
        entry.unpublish()
        invalidate_entry_cache(entry)
        dispatch_webhook_event.delay(str(entry.organization_id), "content.expired", {"id": str(entry.id)})

    return {"published": published, "expired": expired.count()}
