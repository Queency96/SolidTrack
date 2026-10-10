"""
Common maintenance tasks.

Currently:

    - cleanup_ip_state_mappings
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from common.models import (
    MAPPING_TTL_DAYS,
    IPStateMapping,
)


logger = logging.getLogger(__name__)


@shared_task(
    name="common.cleanup_ip_state_mappings",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=300,
    retry_kwargs={"max_retries": 2},
)
def cleanup_ip_state_mappings(self):
    """
    Delete IPStateMapping rows with no recent evidence.

    Mappings expire after MAPPING_TTL_DAYS (90 days) without
    a new vote. Handles carrier IP reassignment.

    Runs daily.
    """

    cutoff = timezone.now() - timedelta(
        days=MAPPING_TTL_DAYS,
    )

    queryset = IPStateMapping.objects.filter(
        last_seen_at__lt=cutoff,
    )

    total = queryset.count()

    if total == 0:
        return {"deleted": 0}

    queryset.delete()

    logger.info(
        "IPStateMapping cleanup: deleted %s stale rows.",
        total,
    )

    return {"deleted": total}