"""
Rider earning settlement service.

Credits riders for completed assignments by writing a
WalletTransaction directly, mirroring RefundService's
pattern for money-out operations.

Every settlement is idempotent and keyed on a deterministic
reference, so retries cannot double-credit.
"""

import logging
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.utils import timezone
from riders.models import RiderEarning
from wallet.models import Wallet, WalletTransaction


logger = logging.getLogger(__name__)


class RiderEarningService:
    """
    Idempotent settlement writer for RiderEarning rows.
    """

    SETTLEMENT_REFERENCE_PREFIX = "RIDER-EARNING-"

    # ==================================================
    # Public API
    # ==================================================

    @classmethod
    @transaction.atomic
    def settle(cls, *, earning):
        """
        Settle a single RiderEarning by crediting the rider's
        wallet.

        Idempotent: if the earning is already SETTLED, returns
        the existing WalletTransaction without crediting again.

        Returns:
            WalletTransaction | None
            None when the earning has zero net amount.
        """

        if earning is None:
            raise ValueError("Earning is required.")

        # --------------------------------------------------
        # Lock the earning row.
        # --------------------------------------------------

        earning = (
            RiderEarning.objects
            .select_for_update()
            .select_related("rider", "assignment")
            .get(pk=earning.pk)
        )

        # --------------------------------------------------
        # Already settled — return existing transaction.
        # --------------------------------------------------

        if earning.status == RiderEarning.Status.SETTLED:

            if earning.wallet_transaction_id is not None:
                return earning.wallet_transaction

            return None

        # --------------------------------------------------
        # Only PENDING rows can be settled. FAILED rows
        # must be reset to PENDING before retry.
        # --------------------------------------------------

        if earning.status != RiderEarning.Status.PENDING:

            logger.warning(
                "Cannot settle earning %s in status %s.",
                earning.pk,
                earning.status,
            )
            return None

        rider = earning.rider

        # --------------------------------------------------
        # Resolve wallet by explicit query.
        # --------------------------------------------------

        wallet = (
            Wallet.objects
            .select_for_update()
            .filter(user=rider)
            .first()
        )

        if wallet is None:

            cls._mark_failed(
                earning=earning,
                reason="Rider does not have a wallet.",
            )

            logger.warning(
                "Rider %s has no wallet; earning %s FAILED.",
                rider.pk,
                earning.pk,
            )

            return None

        # --------------------------------------------------
        # Zero-value earning — mark settled without a
        # wallet transaction.
        # --------------------------------------------------

        if earning.net_amount <= Decimal("0.00"):

            earning.status = RiderEarning.Status.SETTLED
            earning.settled_at = timezone.now()
            earning.save(
                update_fields=[
                    "status",
                    "settled_at",
                    "updated_at",
                ],
            )

            return None

        # --------------------------------------------------
        # Idempotency reference.
        # --------------------------------------------------

        reference = cls._settlement_reference(earning=earning)

        existing = (
            WalletTransaction.objects
            .filter(reference=reference)
            .first()
        )

        if existing is not None:

            # Link the existing transaction to the earning
            # and mark SETTLED — covers the race where
            # another worker wrote the row but crashed
            # before updating the earning.
            earning.status = RiderEarning.Status.SETTLED
            earning.settled_at = timezone.now()
            earning.wallet_transaction = existing
            earning.save(
                update_fields=[
                    "status",
                    "settled_at",
                    "wallet_transaction",
                    "updated_at",
                ],
            )

            return existing

        # --------------------------------------------------
        # Write the transaction.
        # --------------------------------------------------

        balance_before = wallet.balance
        balance_after = balance_before + earning.net_amount

        try:

            transaction_row = WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=(
                    WalletTransaction.TransactionType.CREDIT
                ),
                amount=earning.net_amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference=reference,
                description=(
                    f"Delivery earnings for assignment "
                    f"{earning.assignment_id}"
                ),
                status=WalletTransaction.Status.SUCCESS,
            )

        except IntegrityError:

            # Another worker won the race. Link and mark
            # settled against the existing row.
            existing = (
                WalletTransaction.objects
                .filter(reference=reference)
                .first()
            )

            if existing is not None:

                earning.status = RiderEarning.Status.SETTLED
                earning.settled_at = timezone.now()
                earning.wallet_transaction = existing
                earning.save(
                    update_fields=[
                        "status",
                        "settled_at",
                        "wallet_transaction",
                        "updated_at",
                    ],
                )

                return existing

            raise

        # --------------------------------------------------
        # Credit the wallet balance.
        # --------------------------------------------------

        wallet.balance = balance_after
        wallet.save(update_fields=["balance"])

        # --------------------------------------------------
        # Mark the earning settled.
        # --------------------------------------------------

        earning.status = RiderEarning.Status.SETTLED
        earning.settled_at = timezone.now()
        earning.wallet_transaction = transaction_row
        earning.save(
            update_fields=[
                "status",
                "settled_at",
                "wallet_transaction",
                "updated_at",
            ],
        )

        logger.info(
            "Settled %s to rider %s for earning %s.",
            earning.net_amount,
            rider.pk,
            earning.pk,
        )

        return transaction_row

    # ==================================================
    # Helpers
    # ==================================================

    @classmethod
    def _settlement_reference(cls, *, earning):

        return (
            f"{cls.SETTLEMENT_REFERENCE_PREFIX}"
            f"{earning.pk}"
        )

    @staticmethod
    def _mark_failed(*, earning, reason):

        earning.status = RiderEarning.Status.FAILED
        earning.failure_reason = str(reason)[:1000]
        earning.save(
            update_fields=[
                "status",
                "failure_reason",
                "updated_at",
            ],
        )