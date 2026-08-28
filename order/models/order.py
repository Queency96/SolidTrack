from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
import uuid


class Order(models.Model):
    """
    Represents a customer's completed or in-progress purchase.

    An Order is created from a customer's Cart during checkout.

    Unlike Cart data, Order data represents a historical
    transaction and should not depend on mutable product
    information after checkout.

    Order
        ├── Customer
        ├── OrderItems
        ├── Payment
        └── Delivery
    """

    # ==================================================
    # Order Status
    # ==================================================

    class Status(models.TextChoices):

        PENDING = (
            "pending",
            "Pending",
        )

        CONFIRMED = (
            "confirmed",
            "Confirmed",
        )

        PROCESSING = (
            "processing",
            "Processing",
        )

        READY_FOR_DISPATCH = (
            "ready_for_dispatch",
            "Ready for Dispatch",
        )

        OUT_FOR_DELIVERY = (
            "out_for_delivery",
            "Out for Delivery",
        )

        DELIVERED = (
            "delivered",
            "Delivered",
        )

        CANCELLED = (
            "cancelled",
            "Cancelled",
        )

        FAILED = (
            "failed",
            "Failed",
        )

    # ==================================================
    # Payment Status
    # ==================================================

    class PaymentStatus(models.TextChoices):

        PENDING = (
            "pending",
            "Pending",
        )

        PROCESSING = (
            "processing",
            "Processing",
        )

        PAID = (
            "paid",
            "Paid",
        )

        FAILED = (
            "failed",
            "Failed",
        )

        REFUNDED = (
            "refunded",
            "Refunded",
        )

        PARTIALLY_REFUNDED = (
            "partially_refunded",
            "Partially Refunded",
        )

    # ==================================================
    # Payment Method
    # ==================================================

    class PaymentMethod(models.TextChoices):

        WALLET = (
            "wallet",
            "Wallet",
        )

        CARD = (
            "card",
            "Card",
        )

        BANK_TRANSFER = (
            "bank_transfer",
            "Bank Transfer",
        )

        CASH = (
            "cash",
            "Cash",
        )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Customer
    # ==================================================

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )

    # ==================================================
    # Order Number
    # ==================================================

    order_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
    )

    # ==================================================
    # Status
    # ==================================================

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # ==================================================
    # Payment
    # ==================================================

    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        blank=True,
        default="",
    )

    # ==================================================
    # Pricing
    # ==================================================

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    delivery_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    service_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    insurance_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ==================================================
    # Currency
    # ==================================================

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    # ==================================================
    # Notes
    # ==================================================

    customer_note = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Timestamps
    # ==================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "customer",
                    "-created_at",
                ],
            ),

            models.Index(
                fields=[
                    "status",
                    "-created_at",
                ],
            ),

            models.Index(
                fields=[
                    "payment_status",
                    "-created_at",
                ],
            ),

            models.Index(
                fields=[
                    "customer",
                    "status",
                ],
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        return (
            f"Order {self.order_number} - "
            f"{self.customer.email}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate order pricing and status configuration.
        """

        # ----------------------------------------------
        # Monetary values
        # ----------------------------------------------

        monetary_fields = [
            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "tax_amount",
            "total_amount",
        ]

        for field_name in monetary_fields:

            value = getattr(
                self,
                field_name,
            )

            if value < Decimal("0.00"):

                raise ValidationError(
                    {
                        field_name: (
                            f"{field_name.replace('_', ' ').capitalize()} "
                            "cannot be negative."
                        )
                    }
                )

        # ----------------------------------------------
        # Total calculation
        # ----------------------------------------------

        calculated_total = (
            self.subtotal
            + self.delivery_fee
            + self.service_fee
            + self.insurance_fee
            + self.tax_amount
            - self.discount_amount
        )

        if calculated_total < Decimal("0.00"):

            calculated_total = Decimal(
                "0.00"
            )

        if self.total_amount != calculated_total:

            raise ValidationError(
                {
                    "total_amount": (
                        "Order total does not match "
                        "the order pricing breakdown."
                    )
                }
            )

    # ==================================================
    # Save
    # ==================================================

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    # ==================================================
    # Item Count
    # ==================================================

    @property
    def items_count(self):
        """
        Return the number of distinct order items.
        """

        return self.items.count()

    # ==================================================
    # Total Quantity
    # ==================================================

    @property
    def total_items(self):
        """
        Return the total quantity across all order items.
        """

        return sum(
            (
                item.quantity
                for item in self.items.all()
            ),
            0,
        )

    # ==================================================
    # Paid
    # ==================================================

    @property
    def is_paid(self):
        """
        Determine whether the order has been paid.
        """

        return (
            self.payment_status
            == self.PaymentStatus.PAID
        )

    # ==================================================
    # Cancelled
    # ==================================================

    @property
    def is_cancelled(self):
        """
        Determine whether the order is cancelled.
        """

        return (
            self.status
            == self.Status.CANCELLED
        )

    # ==================================================
    # Completed
    # ==================================================

    @property
    def is_completed(self):
        """
        Determine whether the order has been delivered.
        """

        return (
            self.status
            == self.Status.DELIVERED
        )

    # ==================================================
    # Can Cancel
    # ==================================================

    @property
    def can_cancel(self):
        """
        Determine whether the order can still be
        cancelled.
        """

        return self.status in [
            self.Status.PENDING,
            self.Status.CONFIRMED,
            self.Status.PROCESSING,
        ]