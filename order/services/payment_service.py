import hashlib
import hmac
import logging
from decimal import Decimal, ROUND_HALF_UP
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from ..models import Order, OrderPayment
from wallet.services import WalletService


logger = logging.getLogger(__name__)


class PaymentService:
    """
    Handles order payment initialization, verification,
    wallet payments, Paystack payments, and final settlement.

    Payment flow:

        OrderPayment(PENDING)
                |
                +-- Wallet
                |
                +-- Paystack
                        |
                        v
                  Paystack API
                        |
                        v
                    Webhook
                        |
                        v
                  verify_payment()
                        |
                        v
                mark_payment_successful()
                        |
                        v
                   Order = PAID
    """

    PAYSTACK_BASE_URL = (
        "https://api.paystack.co"
    )

    # ==================================================
    # Initialize
    # ==================================================

    @classmethod
    def initialize(
        cls,
        *,
        payment,
        callback_url=None,
        channels=None,
    ):
        """
        Initialize an OrderPayment.

        Wallet payments are processed immediately.

        Gateway payments are initialized with the
        configured payment provider.
        """

        if payment.status != (
            OrderPayment.PaymentStatus.PENDING
        ):
            raise ValueError(
                "Payment is no longer pending."
            )

        if payment.amount <= Decimal("0.00"):
            raise ValueError(
                "Payment amount must be greater than zero."
            )

        if payment.payment_method == (
            OrderPayment.PaymentMethod.WALLET
        ):
            return cls._process_wallet_payment(
                payment=payment,
            )

        if payment.provider == (
            OrderPayment.PaymentProvider.PAYSTACK
        ):
            return cls._initialize_paystack(
                payment=payment,
                callback_url=callback_url,
                channels=channels,
            )

        raise ValueError(
            "Unsupported payment provider."
        )

    # ==================================================
    # Wallet
    # ==================================================

    @classmethod
    @transaction.atomic
    def _process_wallet_payment(
        cls,
        *,
        payment,
    ):
        """
        Debit the customer's wallet and settle the
        order payment atomically.
        """

        payment = (
            OrderPayment.objects
            .select_for_update()
            .select_related(
                "order",
                "user",
            )
            .get(
                pk=payment.pk,
            )
        )

        if payment.status != (
            OrderPayment.PaymentStatus.PENDING
        ):
            return payment

        order = (
            Order.objects
            .select_for_update()
            .get(
                pk=payment.order_id,
            )
        )

        if order.payment_status == (
            Order.PaymentStatus.PAID
        ):
            return payment

        wallet = cls._get_customer_wallet(
            payment.user,
        )

        WalletService.debit(
            wallet=wallet,
            amount=payment.amount,
            description=(
                f"Payment for order "
                f"{order.order_number}"
            ),
        )

        payment.status = (
            OrderPayment.PaymentStatus.SUCCESSFUL
        )

        payment.paid_at = timezone.now()

        payment.gateway_response = {
            "provider": "wallet",
            "status": "success",
        }

        payment.save(
            update_fields=[
                "status",
                "paid_at",
                "gateway_response",
                "updated_at",
            ]
        )

        cls._mark_order_paid(
            order=order,
            payment=payment,
        )

        return payment

    # ==================================================
    # Wallet Lookup
    # ==================================================

    @staticmethod
    def _get_customer_wallet(
        user,
    ):
        """
        Retrieve the customer's wallet.

        Adjust this lookup if your Wallet model uses a
        different ownership field.
        """

        wallet = getattr(
            user,
            "wallet",
            None,
        )

        if wallet is None:
            raise ValueError(
                "Customer does not have a wallet."
            )

        return wallet

    # ==================================================
    # Paystack Initialize
    # ==================================================

    @classmethod
    def _initialize_paystack(
        cls,
        *,
        payment,
        callback_url=None,
        channels=None,
    ):
        """
        Initialize a Paystack transaction.

        Paystack expects amount in the smallest currency
        denomination, e.g. NGN kobo.
        """

        secret_key = getattr(
            settings,
            "PAYSTACK_SECRET_KEY",
            None,
        )

        if not secret_key:
            raise ValueError(
                "PAYSTACK_SECRET_KEY is not configured."
            )

        payment = (
            OrderPayment.objects
            .select_for_update()
            .select_related(
                "order",
                "user",
            )
            .get(
                pk=payment.pk,
            )
        )

        if payment.status != (
            OrderPayment.PaymentStatus.PENDING
        ):
            raise ValueError(
                "Payment is no longer pending."
            )

        order = payment.order
        customer = payment.user

        reference = cls._paystack_reference(
            payment=payment,
        )

        amount = cls._to_subunit(
            payment.amount,
        )

        payload = {
            "email": customer.email,
            "amount": str(amount),
            "currency": payment.currency,
            "reference": reference,
            "metadata": {
                "order_id": str(order.id),
                "order_number": order.order_number,
                "payment_id": str(payment.id),
                "payment_reference": str(
                    payment.reference
                ),
            },
        }

        if callback_url:
            payload["callback_url"] = callback_url

        if channels:
            payload["channels"] = channels

        headers = {
            "Authorization": (
                f"Bearer {secret_key}"
            ),
            "Content-Type": "application/json",
        }

        payment.status = (
            OrderPayment.PaymentStatus.PROCESSING
        )

        payment.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        try:

            response = requests.post(
                (
                    f"{cls.PAYSTACK_BASE_URL}"
                    "/transaction/initialize"
                ),
                json=payload,
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

        except requests.RequestException as exc:

            logger.exception(
                "Paystack initialization failed."
            )

            payment.status = (
                OrderPayment.PaymentStatus.FAILED
            )

            payment.failure_reason = str(
                exc
            )

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "updated_at",
                ]
            )

            raise ValueError(
                "Unable to initialize payment."
            ) from exc

        if not data.get("status"):

            payment.status = (
                OrderPayment.PaymentStatus.FAILED
            )

            payment.failure_reason = (
                data.get("message")
                or "Paystack initialization failed."
            )

            payment.gateway_response = data

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "gateway_response",
                    "updated_at",
                ]
            )

            raise ValueError(
                payment.failure_reason
            )

        transaction_data = (
            data.get("data") or {}
        )

        provider_reference = (
            transaction_data.get("reference")
        )

        payment.provider_reference = (
            provider_reference
        )

        payment.gateway_response = data

        payment.save(
            update_fields=[
                "provider_reference",
                "gateway_response",
                "updated_at",
            ]
        )

        return {
            "payment": payment,
            "authorization_url": (
                transaction_data.get(
                    "authorization_url"
                )
            ),
            "access_code": (
                transaction_data.get(
                    "access_code"
                )
            ),
            "reference": provider_reference,
        }

    # ==================================================
    # Paystack Reference
    # ==================================================

    @staticmethod
    def _paystack_reference(
        *,
        payment,
    ):
        """
        Use our internal payment UUID as the gateway
        reference.

        UUID hyphens are valid for Paystack references.
        """

        return str(
            payment.reference
        )

    # ==================================================
    # Verify Paystack
    # ==================================================

    @classmethod
    def verify_paystack_payment(
        cls,
        *,
        reference,
    ):
        """
        Verify a Paystack transaction directly against
        Paystack's API.
        """

        secret_key = getattr(
            settings,
            "PAYSTACK_SECRET_KEY",
            None,
        )

        if not secret_key:
            raise ValueError(
                "PAYSTACK_SECRET_KEY is not configured."
            )

        headers = {
            "Authorization": (
                f"Bearer {secret_key}"
            ),
        }

        try:

            response = requests.get(
                (
                    f"{cls.PAYSTACK_BASE_URL}"
                    "/transaction/verify/"
                    f"{reference}"
                ),
                headers=headers,
                timeout=30,
            )

            response.raise_for_status()

            data = response.json()

        except requests.RequestException as exc:

            logger.exception(
                "Paystack verification failed."
            )

            raise ValueError(
                "Unable to verify payment."
            ) from exc

        if not data.get("status"):

            raise ValueError(
                data.get(
                    "message",
                    "Payment verification failed.",
                )
            )

        return data

    # ==================================================
    # Settle Paystack Payment
    # ==================================================

    @classmethod
    @transaction.atomic
    def settle_paystack_payment(
        cls,
        *,
        reference,
    ):
        """
        Verify and settle a Paystack payment.

        This method is idempotent.

        If the payment has already been successfully
        settled, it simply returns the existing payment.
        """

        payment = (
            OrderPayment.objects
            .select_for_update()
            .select_related(
                "order",
                "user",
            )
            .filter(
                provider_reference=reference,
            )
            .first()
        )

        if payment is None:

            payment = (
                OrderPayment.objects
                .select_for_update()
                .select_related(
                    "order",
                    "user",
                )
                .filter(
                    reference=reference,
                )
                .first()
            )

        if payment is None:
            raise ValueError(
                "Payment transaction not found."
            )

        if payment.status == (
            OrderPayment.PaymentStatus.SUCCESSFUL
        ):
            return payment

        verification = (
            cls.verify_paystack_payment(
                reference=reference,
            )
        )

        transaction_data = (
            verification.get("data") or {}
        )

        gateway_status = transaction_data.get(
            "status"
        )

        gateway_amount = transaction_data.get(
            "amount"
        )

        expected_amount = cls._to_subunit(
            payment.amount,
        )

        # ----------------------------------------------
        # Reference validation
        # ----------------------------------------------

        gateway_reference = (
            transaction_data.get("reference")
        )

        if gateway_reference != reference:

            raise ValueError(
                "Payment reference mismatch."
            )

        # ----------------------------------------------
        # Amount validation
        # ----------------------------------------------

        try:

            gateway_amount = int(
                gateway_amount
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "Invalid payment amount returned "
                "by payment provider."
            )

        if gateway_amount != expected_amount:

            payment.status = (
                OrderPayment.PaymentStatus.FAILED
            )

            payment.failure_reason = (
                "Payment amount does not match "
                "the order amount."
            )

            payment.gateway_response = (
                verification
            )

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "gateway_response",
                    "updated_at",
                ]
            )

            raise ValueError(
                "Payment amount does not match "
                "the order amount."
            )

        # ----------------------------------------------
        # Gateway status
        # ----------------------------------------------

        if gateway_status != "success":

            payment.gateway_response = (
                verification
            )

            payment.failure_reason = (
                f"Paystack transaction status: "
                f"{gateway_status}"
            )

            payment.status = (
                OrderPayment.PaymentStatus.FAILED
            )

            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "gateway_response",
                    "updated_at",
                ]
            )

            return payment

        # ----------------------------------------------
        # Successful payment
        # ----------------------------------------------

        payment.status = (
            OrderPayment.PaymentStatus.SUCCESSFUL
        )

        payment.paid_at = timezone.now()

        payment.provider_reference = (
            gateway_reference
        )

        payment.gateway_response = (
            verification
        )

        payment.save(
            update_fields=[
                "status",
                "paid_at",
                "provider_reference",
                "gateway_response",
                "updated_at",
            ]
        )

        order = (
            Order.objects
            .select_for_update()
            .get(
                pk=payment.order_id,
            )
        )

        cls._mark_order_paid(
            order=order,
            payment=payment,
        )

        return payment

    # ==================================================
    # Mark Order Paid
    # ==================================================

    @staticmethod
    def _mark_order_paid(
        *,
        order,
        payment,
    ):
        """
        Update the aggregate Order payment state.

        This operation must only be called after the
        payment transaction itself has been verified.
        """

        if order.payment_status == (
            Order.PaymentStatus.PAID
        ):
            return

        order.payment_status = (
            Order.PaymentStatus.PAID
        )

        order.paid_at = (
            payment.paid_at
            or timezone.now()
        )

        if order.status == (
            Order.Status.PENDING
        ):
            order.status = (
                Order.Status.CONFIRMED
            )

            order.confirmed_at = (
                timezone.now()
            )

        order.save(
            update_fields=[
                "payment_status",
                "paid_at",
                "status",
                "confirmed_at",
                "updated_at",
            ]
        )

    # ==================================================
    # Webhook Signature
    # ==================================================

    @staticmethod
    def verify_webhook_signature(
        *,
        payload,
        signature,
    ):
        """
        Validate the x-paystack-signature header.

        Paystack signs webhook payloads using HMAC SHA512.
        """

        secret_key = getattr(
            settings,
            "PAYSTACK_SECRET_KEY",
            None,
        )

        if not secret_key:
            return False

        expected_signature = hmac.new(
            secret_key.encode("utf-8"),
            payload,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(
            expected_signature,
            signature or "",
        )

    # ==================================================
    # Webhook
    # ==================================================

    @classmethod
    def handle_webhook(
        cls,
        *,
        payload,
        signature,
    ):
        """
        Process a Paystack webhook payload.

        The caller should provide the raw request body
        as `payload` and the x-paystack-signature header
        as `signature`.
        """

        if not cls.verify_webhook_signature(
            payload=payload,
            signature=signature,
        ):
            raise PermissionError(
                "Invalid Paystack webhook signature."
            )

        import json

        try:

            event = json.loads(
                payload.decode("utf-8")
            )

        except (
            ValueError,
            UnicodeDecodeError,
        ) as exc:

            raise ValueError(
                "Invalid webhook payload."
            ) from exc

        event_name = event.get(
            "event"
        )

        data = event.get(
            "data"
        ) or {}

        reference = data.get(
            "reference"
        )

        if not reference:
            return {
                "processed": False,
                "reason": "Missing transaction reference.",
            }

        # ----------------------------------------------
        # Successful transaction
        # ----------------------------------------------

        if event_name == "charge.success":

            payment = (
                cls.settle_paystack_payment(
                    reference=reference,
                )
            )

            return {
                "processed": True,
                "event": event_name,
                "payment_id": str(
                    payment.id
                ),
            }

        # ----------------------------------------------
        # Other events
        # ----------------------------------------------

        logger.info(
            "Ignoring Paystack event: %s",
            event_name,
        )

        return {
            "processed": False,
            "event": event_name,
        }

    # ==================================================
    # Currency Conversion
    # ==================================================

    @staticmethod
    def _to_subunit(
        amount,
    ):
        """
        Convert major currency units to the smallest
        currency denomination.

        Example:

            ₦10.50 -> 1050
        """

        amount = Decimal(
            str(amount)
        )

        return int(
            (
                amount
                * Decimal("100")
            ).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )