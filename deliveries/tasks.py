"""
Delivery-related Celery tasks.

Handles two concerns:

    1. Expiring stale delivery offers so redispatch can proceed.
    2. (Placeholder for future delivery tasks.)
"""

import logging

from celery import shared_task
from django.utils import timezone

from deliveries.models import DeliveryOffer


logger = logging.getLogger(__name__)


# Cap per run to bound task execution time. Remaining offers are
# picked up on the next beat cycle.
EXPIRY_BATCH_SIZE = 50


@shared_task(
    name="deliveries.expire_stale_offers",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={"max_retries": 3},
)
def expire_stale_offers(self):
    """
    Find PENDING offers whose expires_at has passed and
    dispatch them through DispatchCoordinator.offer_expired.

    The coordinator handles:
        - marking the offer EXPIRED
        - notifying the customer
        - redispatching the delivery if configured

    Runs every 60 seconds via Celery beat.
    """

    # Lazy import to avoid a circular dependency at module load.
    from deliveries.dispatch.coordinator import DispatchCoordinator

    now = timezone.now()

    expired_ids = list(
        DeliveryOffer.objects
        .filter(
            status=DeliveryOffer.Status.PENDING,
            expires_at__lte=now,
        )
        .order_by("expires_at")
        .values_list("id", flat=True)[:EXPIRY_BATCH_SIZE]
    )

    if not expired_ids:
        return {"expired": 0, "skipped": 0, "failed": 0}

    expired = 0
    skipped = 0
    failed = 0

    for offer_id in expired_ids:

        try:
            offer = (
                DeliveryOffer.objects
                .select_related("delivery", "rider")
                .get(pk=offer_id)
            )
        except DeliveryOffer.DoesNotExist:
            skipped += 1
            continue

        # Re-check inside the loop in case a concurrent task or
        # request resolved it between the query and this call.
        if offer.status != DeliveryOffer.Status.PENDING:
            skipped += 1
            continue

        try:
            DispatchCoordinator.offer_expired(offer)
            expired += 1

        except Exception:
            # The coordinator handles InvalidOfferState
            # internally and returns a failed result for
            # races where the offer was already resolved.
            # Any exception that reaches here is unexpected.
            logger.exception(
                "Failed to expire offer %s",
                offer_id,
            )
            failed += 1

    logger.info(
        "Offer expiry sweep: expired=%s skipped=%s failed=%s",
        expired,
        skipped,
        failed,
    )

    return {
        "expired": expired,
        "skipped": skipped,
        "failed": failed,
    }