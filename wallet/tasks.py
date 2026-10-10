"""
Wallet-related Celery tasks.

Currently:

    - settle_rider_earnings
"""

import logging

from celery import shared_task
from django.utils import timezone


logger = logging.getLogger(__name__)


# How long after completion before settlement is attempted.
# Buffer for dispute windows.
SETTLEMENT_DELAY_MINUTES = 60


@shared_task(
    name="wallet.settle_rider_earnings",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=120,
    retry_kwargs={"max_retries": 3},
)
def settle_rider_earnings(self):
    """
    Credit riders for their pending earning ledger entries.

    Runs every 15 minutes via Celery beat.
    """

    from riders.models import RiderEarning
    from riders.services import RiderEarningService

    cutoff = timezone.now() - timezone.timedelta(
        minutes=SETTLEMENT_DELAY_MINUTES,
    )

    candidates = (
        RiderEarning.objects
        .filter(
            status=RiderEarning.Status.PENDING,
            created_at__lte=cutoff,
        )
        .order_by("created_at")[:100]
    )

    settled = 0
    skipped = 0
    failed = 0

    for earning in candidates.iterator():

        try:
            result = RiderEarningService.settle(earning=earning)

            # Refresh to check the outcome.
            earning.refresh_from_db(
                fields=["status"],
            )

            if earning.status == RiderEarning.Status.SETTLED:
                settled += 1
            elif earning.status == RiderEarning.Status.FAILED:
                failed += 1
            else:
                skipped += 1

        except Exception:

            logger.exception(
                "Settlement task failed for earning %s.",
                earning.pk,
            )
            failed += 1

    if settled or failed:
        logger.info(
            "Rider earnings settlement: settled=%s "
            "failed=%s skipped=%s",
            settled,
            failed,
            skipped,
        )

    return {
        "settled": settled,
        "failed": failed,
        "skipped": skipped,
    }