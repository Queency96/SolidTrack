import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class OrderPayment(models.Model):
    """
    Payment transaction associated with an order.

    One order may have multiple payment attempts, but only a
    successful payment should settle the order.
    """

    class PaymentMethod(models.TextChoices):
        CARD = "CARD", "Card"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
        USSD = "USSD", "USSD"
        WALLET = "WALLET", "Wallet"
        CASH = "CASH", "Cash"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCESSFUL = "SUCCESSFUL", "Successful"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"
        PARTIALLY_REFUNDED = (
            "PARTIALLY_REFUNDED",
            "Partially Refunded",
        )

    class PaymentProvider(models.TextChoices):
        PAYSTACK = "PAYSTACK", "Paystack"
        FLUTTERWAVE = "FLUTTERWAVE", "Flutterwave"
        WALLET = "WALLET", "Wallet"
        CASH = "CASH", "Cash"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    order = models.ForeignKey(
        "order.Order",
        on_delete=models.PROTECT,
        related_name="payments",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="order_payments",
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
    )

    provider = models.CharField(
        max_length=30,
        choices=PaymentProvider.choices,
    )

    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    provider_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
    )

    gateway_response = models.JSONField(
        default=dict,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "order_payments"

        indexes = [
            models.Index(
                fields=["order"],
                name="order_payment_order_idx",
            ),
            models.Index(
                fields=["user"],
                name="order_payment_user_idx",
            ),
            models.Index(
                fields=["status"],
                name="order_payment_status_idx",
            ),
            models.Index(
                fields=["provider", "provider_reference"],
                name="order_payment_provider_ref_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="order_payment_created_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.reference} - "
            f"{self.amount} {self.currency} - "
            f"{self.status}"
        )

    def clean(self):
        if self.amount <= 0:
            raise ValidationError(
                {"amount": "Payment amount must be greater than zero."}
            )

        if len(self.currency) != 3:
            raise ValidationError(
                {"currency": "Currency must be a 3-letter ISO code."}
            )

        if (
            self.status == self.PaymentStatus.SUCCESSFUL
            and not self.paid_at
        ):
            raise ValidationError(
                {
                    "paid_at": (
                        "Successful payments must have a "
                        "paid_at timestamp."
                    )
                }
            )

        if (
            self.status in {
                self.PaymentStatus.REFUNDED,
                self.PaymentStatus.PARTIALLY_REFUNDED,
            }
            and not self.refunded_at
        ):
            raise ValidationError(
                {
                    "refunded_at": (
                        "Refunded payments must have a "
                        "refunded_at timestamp."
                    )
                }
            )