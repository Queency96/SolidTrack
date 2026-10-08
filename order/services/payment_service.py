"""
Payment service for order settlement.

Responsibilities
----------------
- Generate Dedicated Virtual Accounts (DVAs) for CASH
  orders
- Initialize card / bank-transfer payments via Paystack
- Verify transactions as a backup for the webhook
- Process Paystack webhooks (charge.success, etc.)

Contract used by CheckoutService
--------------------------------
CheckoutService calls:

    PaymentService.generate_dva(order=..., customer=...)

which returns:

    {
        "reference": "...",           # stored on
                                      # payment.provider_reference
        "account_number": "8xxxxxx",  # 10-digit NUBAN
        "bank_name": "Paystack-Titan",
        "account_name": "Paystack-Titan / <Business> - <Customer>",
    }

Idempotency
-----------
generate_dva is idempotent per order: if a DVA has already
been generated for an OrderPayment, it returns the stored
details without calling Paystack again.

handle_webhook is idempotent per event: it uses the
WalletTransaction reference pattern for wallet credits,
and reads the OrderPayment status before mutating anything.
"""

import hashlib
import hmac
import json
import logging

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from order.models import (
    Order,
    OrderPayment,
)
from wallet.service.wallet_service import WalletService

from .exceptions import (
    InvalidWebhookSignature,
    PaymentProviderError,
    WebhookPayloadError,
)
from .paystack_client import PaystackClient


logger = logging.getLogger(__name__)


class PaymentService:
    """
    Order-facing payment operations.
    """

    # Prefix used for card / bank transfer references.
    TRANSACTION_REFERENCE_PREFIX = "TX-"

    # ==================================================
    # DVA generation (used by CheckoutService)
    # ==================================================

    @classmethod
    @transaction.atomic
    def generate_dva(
        cls,
        *,
        order,
        customer,
    ):
        """
        Generate a Paystack Dedicated Virtual Account for
        a CASH order and attach it to the order's pending
        OrderPayment.

        Idempotent per order: if the order's payment
        already has a DVA (identified by a non-empty
        provider_reference in the DVA namespace), the
        stored details are returned.

        Returns the dict described in the module
        docstring.
        """

        if order is None:
            raise ValueError("Order is required.")

        if customer is None:
            raise ValueError("Customer is required.")

        # --------------------------------------------------
        # Locate the pending CASH payment.
        # --------------------------------------------------

        payment = (
            OrderPayment.objects
            .select_for_update()
            .filter(
                order=order,
                status=OrderPayment.PaymentStatus.PENDING,
            )
            .order_by("-created_at")
            .first()
        )

        if payment is None:

            raise ValueError(
                "Order does not have a pending payment."
            )

        # --------------------------------------------------
        # Idempotency: if a DVA already exists, return it.
        # --------------------------------------------------

        existing = cls._extract_dva_details(payment)

        if existing:
            return existing

        # --------------------------------------------------
        # Build the Paystack request.
        # --------------------------------------------------

        first_name, last_name = cls._split_name(
            customer.get_full_name()
            or customer.email
        )

        # ----------------------------------------------
        # Reference format: DVA-<payment.pk>
        #
        # The webhook uses this to find the
        # OrderPayment on charge.success.
        # ----------------------------------------------

        reference = f"DVA-{payment.pk}"

        try:

            response = (
                PaystackClient.create_dedicated_account(
                    customer_email=customer.email,
                    first_name=first_name,
                    last_name=last_name,
                    phone=getattr(
                        customer,
                        "phone_number",
                        "",
                    )
                    or "",
                    preferred_bank="paystack-titan",
                    metadata={
                        "order_id": str(order.pk),
                        "order_number": order.order_number,
                        "payment_id": str(payment.pk),
                        "reference": reference,
                    },
                )
            )

        except PaymentProviderError as exc:

            logger.exception(
                "DVA generation failed for order %s: %s",
                order.pk,
                exc,
            )

            raise

        data = response.get("data") or {}

        account_number = data.get("account_number")
        bank = data.get("bank") or {}
        bank_name = bank.get("name") or "Paystack-Titan"
        account_name = data.get("account_name") or (
            f"Paystack-Titan / {customer.get_full_name()}"
        )

        if not account_number:

            raise PaymentProviderError(
                "Paystack did not return an account number."
            )

        # --------------------------------------------------
        # Persist the DVA details on the payment.
        # --------------------------------------------------

        payment.provider_reference = reference

        gateway_response = dict(
            payment.gateway_response or {}
        )

        gateway_response["dva"] = {
            "account_number": account_number,
            "bank_name": bank_name,
            "account_name": account_name,
            "paystack_id": data.get("id"),
            "generated_at": timezone.now().isoformat(),
        }

        payment.gateway_response = gateway_response

        payment.save(
            update_fields=[
                "provider_reference",
                "gateway_response",
                "updated_at",
            ],
        )

        return {
            "reference": reference,
            "account_number": account_number,
            "bank_name": bank_name,
            "account_name": account_name,
        }

    # ==================================================
    # Card / transfer initialization
    # ==================================================

    @classmethod
    @transaction.atomic
    def initialize_transaction(
        cls,
        *,
        order,
        customer,
    ):
        """
        Initialize a Paystack transaction for CARD /
        BANK_TRANSFER orders and return the authorization
        URL.

        Idempotent per order: returns the existing
        authorization URL if one has already been
        generated.
        """

        if order is None:
            raise ValueError("Order is required.")

        if customer is None:
            raise ValueError("Customer is required.")

        payment = (
            OrderPayment.objects
            .select_for_update()
            .filter(
                order=order,
                status=OrderPayment.PaymentStatus.PENDING,
            )
            .order_by("-created_at")
            .first()
        )

        if payment is None:

            raise ValueError(
                "Order does not have a pending payment."
            )

        # --------------------------------------------------
        # Reuse existing authorization URL.
        # --------------------------------------------------

        existing = cls._extract_authorization_url(payment)

        if existing:
            return existing

        # --------------------------------------------------
        # Reference format: TX-<payment.pk>
        # --------------------------------------------------

        reference = f"{cls.TRANSACTION_REFERENCE_PREFIX}{payment.pk}"

        callback_url = getattr(
            settings,
            "PAYSTACK_CALLBACK_URL",
            None,
        )

        response = PaystackClient.initialize_transaction(
            email=customer.email,
            amount_kobo=cls._to_kobo(payment.amount),
            reference=reference,
            callback_url=callback_url,
            metadata={
                "order_id": str(order.pk),
                "order_number": order.order_number,
                "payment_id": str(payment.pk),
            },
        )

        data = response.get("data") or {}

        authorization_url = data.get("authorization_url")

        if not authorization_url:

            raise PaymentProviderError(
                "Paystack did not return an "
                "authorization URL."
            )

        payment.provider_reference = reference

        gateway_response = dict(
            payment.gateway_response or {}
        )

        gateway_response["transaction"] = {
            "authorization_url": authorization_url,
            "access_code": data.get("access_code"),
            "reference": data.get("reference") or reference,
            "initialized_at": timezone.now().isoformat(),
        }

        payment.gateway_response = gateway_response

        payment.save(
            update_fields=[
                "provider_reference",
                "gateway_response",
                "updated_at",
            ],
        )

        return {
            "authorization_url": authorization_url,
            "access_code": data.get("access_code"),
            "reference": data.get("reference") or reference,
        }

    # ==================================================
    # Transaction verification (backup for the webhook)
    # ==================================================

    @classmethod
    @transaction.atomic
    def verify_transaction(
        cls,
        *,
        order,
    ):
        """
        Verify a payment directly with Paystack.

        Safe to call after a webhook (idempotent) or in
        place of one when the client returns from
        Paystack but the webhook has not yet fired.
        """

        payment = (
            OrderPayment.objects
            .select_for_update()
            .filter(order=order)
            .order_by("-created_at")
            .first()
        )

        if payment is None:
            raise ValueError(
                "Order does not have a payment."
            )

        if payment.status == (
            OrderPayment.PaymentStatus.SUCCESSFUL
        ):
            return payment

        reference = payment.provider_reference

        if not reference:

            raise ValueError(
                "Payment does not have a provider reference."
            )

        response = PaystackClient.verify_transaction(
            reference=reference,
        )

        data = response.get("data") or {}

        if data.get("status") != "success":

            return payment

        cls._settle_order_payment(
            payment=payment,
            provider_payload=data,
        )

        return payment

    # ==================================================
    # Webhook handling
    # ==================================================

    @classmethod
    def handle_webhook(
        cls,
        *,
        payload: bytes,
        signature: str,
    ) -> None:
        """
        Verify and process a Paystack webhook.

        Raises InvalidWebhookSignature on HMAC mismatch
        and WebhookPayloadError on malformed payloads.
        """

        cls._verify_signature(
            payload=payload,
            signature=signature,
        )

        try:
            body = json.loads(payload)

        except json.JSONDecodeError as exc:

            raise WebhookPayloadError(
                "Payload is not valid JSON."
            ) from exc

        event_type = body.get("event")

        if not event_type:

            raise WebhookPayloadError(
                "Missing event type."
            )

        data = body.get("data") or {}

        handler = cls._EVENT_HANDLERS.get(event_type)

        if handler is None:

            logger.info(
                "Ignoring unhandled Paystack event: %s",
                event_type,
            )

            return

        handler(data)

    # ==================================================
    # Event handlers
    # ==================================================

    @classmethod
    @transaction.atomic
    def _handle_charge_success(cls, data):
        """
        Handle charge.success for DVA and card payments.

        The payment is looked up by:

        1. payment.provider_reference == data.reference, or
        2. payment.id == metadata.payment_id
        """

        reference = data.get("reference")

        metadata = data.get("metadata") or {}

        payment = None

        if reference:

            payment = (
                OrderPayment.objects
                .select_for_update()
                .filter(provider_reference=reference)
                .first()
            )

        if payment is None and metadata.get("payment_id"):

            payment = (
                OrderPayment.objects
                .select_for_update()
                .filter(pk=metadata["payment_id"])
                .first()
            )

        if payment is None:

            logger.warning(
                "Paystack webhook did not match any "
                "OrderPayment (reference=%s).",
                reference,
            )

            return

        if payment.status == (
            OrderPayment.PaymentStatus.SUCCESSFUL
        ):

            # Idempotent replay.
            return

        cls._settle_order_payment(
            payment=payment,
            provider_payload=data,
        )

    # ==================================================
    # Settlement
    # ==================================================

    @classmethod
    def _settle_order_payment(
        cls,
        *,
        payment,
        provider_payload,
    ):
        """
        Mark an OrderPayment SUCCESSFUL and update its
        Order.
        """

        now = timezone.now()

        payment.status = (
            OrderPayment.PaymentStatus.SUCCESSFUL
        )
        payment.paid_at = now

        gateway_response = dict(
            payment.gateway_response or {}
        )
        gateway_response["settlement"] = {
            "settled_at": now.isoformat(),
            "provider_reference": provider_payload.get(
                "reference"
            ),
            "amount": str(
                provider_payload.get("amount", "")
            ),
            "channel": provider_payload.get("channel"),
        }

        payment.gateway_response = gateway_response

        payment.save(
            update_fields=[
                "status",
                "paid_at",
                "gateway_response",
                "updated_at",
            ],
        )

        # --------------------------------------------------
        # Update the order.
        # --------------------------------------------------

        order = (
            Order.objects
            .select_for_update()
            .get(pk=payment.order_id)
        )

        if order.payment_status != Order.PaymentStatus.PAID:

            order.payment_status = Order.PaymentStatus.PAID
            order.paid_at = now

            if order.status == Order.Status.PENDING:

                order.status = Order.Status.CONFIRMED
                order.confirmed_at = now

            order.save(
                update_fields=[
                    "payment_status",
                    "paid_at",
                    "status",
                    "confirmed_at",
                    "updated_at",
                ],
            )

    # ==================================================
    # Signature verification
    # ==================================================

    @staticmethod
    def _verify_signature(
        *,
        payload: bytes,
        signature: str,
    ) -> None:
        """
        Compute HMAC-SHA512 over the raw payload and
        compare to the header value using a
        constant-time comparison.
        """

        secret = getattr(
            settings,
            "PAYSTACK_SECRET_KEY",
            "",
        )

        if not secret:

            raise InvalidWebhookSignature(
                "PAYSTACK_SECRET_KEY is not configured."
            )

        computed = hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()

        if not hmac.compare_digest(computed, signature):

            raise InvalidWebhookSignature(
                "Signature mismatch."
            )

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _extract_dva_details(payment):
        """
        Return the stored DVA details for a payment, or
        None when no DVA has been generated.
        """

        gateway_response = payment.gateway_response or {}

        dva = gateway_response.get("dva")

        if not dva:
            return None

        account_number = dva.get("account_number")

        if not account_number:
            return None

        return {
            "reference": payment.provider_reference,
            "account_number": account_number,
            "bank_name": dva.get("bank_name", ""),
            "account_name": dva.get("account_name", ""),
        }

    # ==================================================

    @staticmethod
    def _extract_authorization_url(payment):
        """
        Return the stored authorization URL for a payment,
        or None when none has been generated.
        """

        gateway_response = payment.gateway_response or {}

        transaction = gateway_response.get("transaction")

        if not transaction:
            return None

        url = transaction.get("authorization_url")

        if not url:
            return None

        return {
            "authorization_url": url,
            "access_code": transaction.get("access_code"),
            "reference": transaction.get("reference"),
        }

    # ==================================================

    @staticmethod
    def _split_name(full_name):
        """
        Split a full name into (first, last), tolerating
        empty or single-token names.
        """

        parts = (full_name or "").strip().split()

        if not parts:
            return "", ""

        if len(parts) == 1:
            return parts[0], ""

        return parts[0], " ".join(parts[1:])

    # ==================================================

    @staticmethod
    def _to_kobo(amount) -> int:
        """
        Convert a Decimal amount in NGN to kobo (int).
        """

        return int(
            (Decimal(str(amount)) * Decimal("100"))
            .quantize(Decimal("1"))
        )

    # ==================================================
    # Event dispatch table
    # ==================================================

    # Populated below the class body to allow forward
    # references without circular imports.
    _EVENT_HANDLERS = {}


# ==================================================
# Bind handlers to event names
# ==================================================

PaymentService._EVENT_HANDLERS = {
    "charge.success": PaymentService._handle_charge_success,
}