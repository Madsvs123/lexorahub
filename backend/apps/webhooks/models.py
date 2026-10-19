import hashlib
import hmac
import json

import httpx
from celery import shared_task
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel, UUIDModel


class WebhookEndpoint(UUIDModel, TimeStampedModel):
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE, related_name="webhooks"
    )
    name = models.CharField(max_length=120)
    url = models.URLField()
    secret = models.CharField(max_length=128)
    events = models.JSONField(default=list)  # content.published, content.updated, ...
    is_active = models.BooleanField(default=True)
    publications = models.ManyToManyField("tenancy.Publication", blank=True)
    headers = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]


class WebhookDelivery(UUIDModel, TimeStampedModel):
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name="deliveries")
    event = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    success = models.BooleanField(default=False)
    attempt = models.PositiveIntegerField(default=1)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "webhook deliveries"


@shared_task(name="webhooks.dispatch_event", bind=True, max_retries=5)
def dispatch_webhook_event(self, organization_id: str, event: str, data: dict):
    endpoints = WebhookEndpoint.objects.filter(
        organization_id=organization_id, is_active=True
    )
    for endpoint in endpoints:
        if endpoint.events and event not in endpoint.events and "*" in endpoint.events:
            continue
        _deliver(endpoint, event, data)


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _deliver(endpoint: WebhookEndpoint, event: str, data: dict):
    payload = {
        "event": event,
        "data": data,
        "sent_at": timezone.now().isoformat(),
        "organization_id": str(endpoint.organization_id),
    }
    body = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "X-QuillStack-Event": event,
        "X-QuillStack-Signature": _sign(endpoint.secret, body),
        **(endpoint.headers or {}),
    }
    delivery = WebhookDelivery.objects.create(endpoint=endpoint, event=event, payload=payload)
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(endpoint.url, content=body, headers=headers)
        delivery.response_status = resp.status_code
        delivery.response_body = resp.text[:4000]
        delivery.success = resp.status_code == 200
        delivery.save()
    except Exception as exc:
        delivery.response_body = str(exc)
        delivery.success = False
        delivery.save()
        raise
