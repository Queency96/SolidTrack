"""
Order-related Celery tasks.

Handles three concerns:

    1. Sweeping missing delivery OTPs.
    2. Dispatching scheduled deliveries when their window arrives.
    3. Retrying failed refunds (rare, but belt-and-suspenders).
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from order.models import Order, OrderFulfillment
from wallet.models import WalletTransaction


logger = logging.getLogger(__name__)


# ==================================================
# Missing OTP sweep
# ==================================================


@shared_task(
    name="order.sweep_missing_delivery_otps",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_kwargs={"max_retries": 3},
)
def sweep_missing_delivery_otps(self):
    """
    Find OUT_FOR_DELIVERY fulfillments without a delivery OTP
    and generate one.
    """

    from order.services.order_fulfillment_service import (
        OrderFulfillmentService,
    )

    candidates = (
        OrderFulfillment.objects
        .filter(
            status=OrderFulfillment.Status.OUT_FOR_DELIVERY,
        )
        .filter(
            Q(delivery_otp="")
            | Q(delivery_otp__isnull=True)
        )
    )

    count = 0

    for fulfillment in candidates.iterator():

        try:
            otp = (
                OrderFulfillmentService
                ._ensure_delivery_otp(
                    fulfillment=fulfillment,
                )
            )

            (
                OrderFulfillmentService
                ._notify_customer_delivery_otp(
                    fulfillment=fulfillment,
                    otp=otp,
                )
            )

            count += 1

            logger.info(
                "Sweep issued missing OTP for fulfillment %s",
                fulfillment.pk,
            )

        except Exception:

            logger.exception(
                "Sweep failed for fulfillment %s",
                fulfillment.pk,
            )

    return {"swept": count}


# ==================================================
# Scheduled dispatch
# ==================================================

# Dispatch this many minutes before scheduled_at.
SCHEDULED_DISPATCH_WINDOW_MINUTES = 15


@shared_task(
    name="order.dispatch_scheduled_deliveries",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_kwargs={"max_retries": 3},
)
def dispatch_scheduled_deliveries(self):
    """
    Find fulfillments ready for dispatch whose scheduled_at is
    within SCHEDULED_DISPATCH_WINDOW_MINUTES from now, and
    trigger mark_ready_for_dispatch.

    Runs every 60 seconds via Celery beat.

    The window handles the case where a scheduled delivery was
    set for 2:00 PM and we want the rider en route by then.
    Scheduling dispatch for 15 minutes before means the rider
    has a head start.
    """

    from order.services.order_fulfillment_service import (
        OrderFulfillmentService,
    )

    now = timezone.now()
    window_end = now + timedelta(
        minutes=SCHEDULED_DISPATCH_WINDOW_MINUTES,
    )

    candidates = (
        OrderFulfillment.objects
        .filter(
            status=OrderFulfillment.Status.PACKING,
            delivery_type=OrderFulfillment.DeliveryType.SCHEDULED,
            scheduled_at__isnull=False,
            scheduled_at__lte=window_end,
        )
        .exclude(
            delivery=None,
        )
        .order_by("scheduled_at")
    )

    dispatched = 0
    failed = 0

    for fulfillment in candidates.iterator():

        try:
            OrderFulfillmentService.mark_ready_for_dispatch(
                fulfillment=fulfillment,
            )
            dispatched += 1

            logger.info(
                "Scheduled dispatch fired for fulfillment %s "
                "(scheduled_at=%s)",
                fulfillment.pk,
                fulfillment.scheduled_at,
            )

        except Exception:

            # Common non-fatal cases:
            #   - packages not all READY_FOR_PICKUP yet
            #   - order was cancelled between query and call
            #   - fulfillment already dispatched
            #
            # Log and continue.
            logger.exception(
                "Scheduled dispatch failed for fulfillment %s",
                fulfillment.pk,
            )
            failed += 1

    return {
        "dispatched": dispatched,
        "failed": failed,
    }


# ==================================================
# Refund retry
# ==================================================

# Only retry refunds created in the last N days. Older ones
# are presumed correct (or permanently failed).
REFUND_RETRY_WINDOW_DAYS = 7


@shared_task(
    name="order.retry_failed_refunds",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=300,
    retry_kwargs={"max_retries": 2},
)
def retry_failed_refunds(self):
    """
    Find FAILED refund WalletTransactions and retry them.

    RefundService is idempotent, so retrying is safe — it
    will not double-credit.

    Runs every 15 minutes via Celery beat.
    """

    from common.services.refund_service import RefundService
    from deliveries.models import DeliveryAssignment  # noqa: F401

    cutoff = timezone.now() - timedelta(
        days=REFUND_RETRY_WINDOW_DAYS,
    )

    failed_refunds = (
        WalletTransaction.objects
        .filter(
            transaction_type=(
                WalletTransaction.TransactionType.REFUND
            ),
            status=WalletTransaction.Status.FAILED,
            created_at__gte=cutoff,
        )
        .order_by("created_at")[:50]
    )

    retried = 0
    recovered = 0

    for tx in failed_refunds:

        retried += 1

        # The refund transaction was created via
        # RefundService.refund_fulfillment, keyed by
        # reference "REF-FULFILLMENT-<uuid>". Extract the
        # fulfillment id and re-run the refund path.
        reference = tx.reference or ""

        if not reference.startswith("REF-FULFILLMENT-"):
            continue

        fulfillment_id = reference.removeprefix(
            "REF-FULFILLMENT-"
        )

        try:
            fulfillment = (
                OrderFulfillment.objects
                .get(pk=fulfillment_id)
            )
        except (OrderFulfillment.DoesNotExist, ValueError):
            continue

        try:
            new_tx = RefundService.refund_fulfillment(
                fulfillment=fulfillment,
                reason="Retry of failed refund.",
            )

            if new_tx is not None and new_tx.status == (
                WalletTransaction.Status.SUCCESS
            ):
                recovered += 1

        except Exception:

            logger.exception(
                "Refund retry failed for fulfillment %s",
                fulfillment_id,
            )

    if retried:
        logger.info(
            "Refund retry: retried=%s recovered=%s",
            retried,
            recovered,
        )

    return {
        "retried": retried,
        "recovered": recovered,
    }