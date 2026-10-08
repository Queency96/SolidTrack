"""
Refund orchestration for fulfillment failures.

Refunds are written directly to WalletTransaction with a
deterministic reference so retries cannot double-credit.

Refund rules
------------
For a fulfillment that cannot be completed:

    refundable_subtotal = sum of subtotals of all
                          UNAVAILABLE items where
                          is_perishable is False

    refund              = refundable_subtotal
                        + 100% of fulfillment's
                          delivery_fee
                        + 100% of fulfillment's
                          service_fee
                        + 100% of fulfillment's
                          insurance_fee
                        - fulfillment's discount_amount

Perishable items are excluded from the refund by policy.
Fees are returned in full because the fulfillment did not
complete and no delivery occurred.
"""

import logging
from decimal import Decimal

from django.db import transaction

from order.models import OrderFulfillment, OrderItem
from wallet.models import WalletTransaction
from wallet.service.wallet_service import WalletService


logger = logging.getLogger(__name__)


class RefundService:
    """
    Idempotent refund writer for fulfillment failures.
    """

    REFUND_REFERENCE_PREFIX = "REF-FULFILLMENT-"

    # ==================================================
    # Public API
    # ==================================================

    @classmethod
    @transaction.atomic
    def refund_fulfillment(cls, *, fulfillment, reason=""):
        """
        Refund the customer for a failed fulfillment.

        Idempotent: repeated calls with the same fulfillment
        return the existing WalletTransaction without
        crediting again.

        Returns:
            WalletTransaction | None
            None when the computed refund is zero.
        """

        if fulfillment is None:
            raise ValueError("Fulfillment is required.")

        if fulfillment.order is None:
            raise ValueError("Fulfillment has no order.")

        customer = fulfillment.order.customer

        if customer is None:
            raise ValueError("Fulfillment order has no customer.")

        wallet = getattr(customer, "wallet", None)

        if wallet is None:
            raise ValueError("Customer does not have a wallet.")

        reference = cls._idempotency_reference(fulfillment=fulfillment)

        # --------------------------------------------------
        # Idempotency: return existing refund if present.
        # --------------------------------------------------

        existing = (
            WalletTransaction.objects
            .filter(reference=reference)
            .first()
        )

        if existing is not None:
            return existing

        # --------------------------------------------------
        # Compute refund.
        # --------------------------------------------------

        amount, breakdown = cls.compute_refund(fulfillment=fulfillment)

        if amount <= Decimal("0.00"):
            logger.info(
                "Refund for fulfillment %s computed to zero "
                "(refundable=%s, perishable=%s)",
                fulfillment.pk,
                breakdown["refundable_subtotal"],
                breakdown["non_refundable_subtotal"],
            )
            return None

        # --------------------------------------------------
        # Lock the wallet row and write the transaction.
        # --------------------------------------------------

        wallet = (
            wallet.__class__.objects
            .select_for_update()
            .get(pk=wallet.pk)
        )

        balance_before = wallet.balance
        balance_after = balance_before + amount

        description = cls._build_description(
            fulfillment=fulfillment,
            breakdown=breakdown,
            reason=reason,
        )

        transaction_row = WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=WalletTransaction.TransactionType.REFUND,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference=reference,
            description=description,
            status=WalletTransaction.Status.SUCCESS,
        )

        wallet.balance = balance_after
        wallet.save(update_fields=["balance"])

        logger.info(
            "Refunded %s to wallet %s for fulfillment %s",
            amount,
            wallet.pk,
            fulfillment.pk,
        )

        return transaction_row

    # ==================================================
    # Computation
    # ==================================================

    @classmethod
    def compute_refund(cls, *, fulfillment):
        """
        Compute the refund amount and breakdown for a
        fulfillment.

        Returns:
            (amount, breakdown_dict)
        """

        unavailable_items = list(
            OrderItem.objects
            .filter(
                fulfillment=fulfillment,
                fulfillment_status=(
                    OrderItem.FulfillmentStatus.UNAVAILABLE
                ),
            )
        )

        refundable_subtotal = Decimal("0.00")
        non_refundable_subtotal = Decimal("0.00")

        for item in unavailable_items:
            subtotal = Decimal(str(item.subtotal))

            if item.is_refundable:
                refundable_subtotal += subtotal
            else:
                non_refundable_subtotal += subtotal

        # --------------------------------------------------
        # Fees: 100% refunded on fulfillment failure.
        # --------------------------------------------------

        delivery_fee = Decimal(str(fulfillment.delivery_fee or 0))
        service_fee = Decimal(str(fulfillment.service_fee or 0))
        insurance_fee = Decimal(str(fulfillment.insurance_fee or 0))
        discount_amount = Decimal(str(fulfillment.discount_amount or 0))

        fees_refunded = (
            delivery_fee + service_fee + insurance_fee
        )

        amount = (
            refundable_subtotal
            + fees_refunded
            - discount_amount
        )

        if amount < Decimal("0.00"):
            amount = Decimal("0.00")

        amount = amount.quantize(Decimal("0.01"))

        return amount, {
            "refundable_subtotal": refundable_subtotal.quantize(
                Decimal("0.01")
            ),
            "non_refundable_subtotal": non_refundable_subtotal.quantize(
                Decimal("0.01")
            ),
            "delivery_fee": delivery_fee.quantize(Decimal("0.01")),
            "service_fee": service_fee.quantize(Decimal("0.01")),
            "insurance_fee": insurance_fee.quantize(Decimal("0.01")),
            "fees_refunded": fees_refunded.quantize(Decimal("0.01")),
            "discount_amount": discount_amount.quantize(Decimal("0.01")),
            "total": amount,
        }

    # ==================================================
    # Helpers
    # ==================================================

    @classmethod
    def _idempotency_reference(cls, *, fulfillment):
        return f"{cls.REFUND_REFERENCE_PREFIX}{fulfillment.pk}"

    @staticmethod
    def _build_description(*, fulfillment, breakdown, reason):
        parts = [
            f"Refund for fulfillment {fulfillment.pk}",
        ]

        if reason:
            parts.append(f"Reason: {reason}")

        parts.append(
            f"Refundable items: {breakdown['refundable_subtotal']}"
        )

        if breakdown["non_refundable_subtotal"] > Decimal("0.00"):
            parts.append(
                f"Perishable items not refunded: "
                f"{breakdown['non_refundable_subtotal']}"
            )

        parts.append(
            f"Fees refunded: {breakdown['fees_refunded']}"
        )

        return " | ".join(parts)