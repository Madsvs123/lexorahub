"""Celery tasks for offer expiry."""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="offers.expire_stale_offers")
def expire_stale_offers():
    from . import services

    count = services.expire_offers()
    logger.info("Expired %s stale offers", count)
    return {"expired": count}
