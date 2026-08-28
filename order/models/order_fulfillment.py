from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class OrderFulfillment(models.Model):
    """
    Represents the fulfillment of an Order by one VendorStore.

    An Order may contain products from multiple stores.

    Example:

        Order
        │
        ├── Fulfillment A → Store A
        │      ├── OrderItems
        │      ├── Packages
        │      └── Delivery
        │
        └── Fulfillment B → Store B
               ├── OrderItems
               ├── Packages
               └── Delivery

    OrderFulfillment is the operational boundary between:

        Order
            ↓
        VendorStore
            ↓
        OrderItems
            ↓
        Packages
            ↓
        Delivery / Dispatch
    """

    # ==================================================
    # Status
    # ==================================================

    class Status(models.TextChoices):

        PENDING = (
            "pending",
            "Pending",
        )

        PROCESSING = (
            "processing",
            "Processing",
        )

        PACKING = (
            "packing",
            "Packing",
        )

        READY_FOR_DISPATCH = (
            "ready_for_dispatch",
            "Ready for Dispatch",
        )

        DISPATCHED = (
            "dispatched",
            "Dispatched",
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
    # ID
    # ==================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Order
    # ==================================================

    order = models.ForeignKey(
        "order.Order",
        on_delete=models.PROTECT,
        related_name="fulfillments",
    )

    # ==================================================
    # Vendor Store
    # ==================================================

    store = models.ForeignKey(
        "vendors.VendorStore",
        on_delete=models.PROTECT,
        related_name="order_fulfillments",
    )

    # ==================================================
    # Store Snapshot
    # ==================================================

    store_name = models.CharField(
        max_length=255,
    )

    store_address_line_1 = models.CharField(
        max_length=255,
    )

    store_address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    store_city = models.CharField(
        max_length=100,
    )

    store_state = models.CharField(
        max_length=100,
    )

    store_country = models.CharField(
        max_length=100,
        default="Nigeria",
    )

    store_postal_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    store_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
    )

    store_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
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
    # Vendor Preparation
    # ==================================================

    vendor_note = models.TextField(
        blank=True,
        default="",
    )

    preparation_note = models.TextField(
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

    processing_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    packing_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ready_for_dispatch_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    dispatched_at = models.DateTimeField(
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

    out_for_delivery_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "created_at",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "order",
                    "store",
                ],
                name="unique_order_store_fulfillment",
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "order",
                ],
            ),

            models.Index(
                fields=[
                    "store",
                ],
            ),

            models.Index(
                fields=[
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "order",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "store",
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "created_at",
                ],
            ),

        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return (
            f"Fulfillment "
            f"{self.id} - "
            f"{self.store_name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        # ----------------------------------------------
        # Order
        # ----------------------------------------------

        if self.order_id is None:

            raise ValidationError(
                {
                    "order": (
                        "A fulfillment must "
                        "belong to an order."
                    )
                }
            )

        # ----------------------------------------------
        # Store
        # ----------------------------------------------

        if self.store_id is None:

            raise ValidationError(
                {
                    "store": (
                        "A fulfillment must "
                        "belong to a store."
                    )
                }
            )

        # ----------------------------------------------
        # Monetary fields
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
        # Total
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
                        "Fulfillment total does not "
                        "match the pricing breakdown."
                    )
                }
            )

        # ----------------------------------------------
        # Status timestamps
        # ----------------------------------------------

        if (
            self.status
            == self.Status.PROCESSING
            and self.processing_at is None
        ):

            raise ValidationError(
                {
                    "processing_at": (
                        "Processing timestamp is "
                        "required for a processing "
                        "fulfillment."
                    )
                }
            )

        if (
            self.status
            == self.Status.PACKING
            and self.packing_at is None
        ):

            raise ValidationError(
                {
                    "packing_at": (
                        "Packing timestamp is "
                        "required for a packing "
                        "fulfillment."
                    )
                }
            )

        if (
            self.status
            == self.Status.READY_FOR_DISPATCH
            and self.ready_for_dispatch_at is None
        ):

            raise ValidationError(
                {
                    "ready_for_dispatch_at": (
                        "Ready-for-dispatch timestamp "
                        "is required."
                    )
                }
            )

        if (
            self.status == self.Status.DISPATCHED
            and self.dispatched_at is None
        ):

            raise ValidationError(
                {
                    "dispatched_at": (
                        "Dispatched timestamp "
                        "is required."
                    )
                }
            )

        if (
            self.status == self.Status.DELIVERED
            and self.delivered_at is None
        ):

            raise ValidationError(
                {
                    "delivered_at": (
                        "Delivered timestamp "
                        "is required."
                    )
                }
            )

        if (
            self.status == self.Status.CANCELLED
            and self.cancelled_at is None
        ):

            raise ValidationError(
                {
                    "cancelled_at": (
                        "Cancelled timestamp "
                        "is required."
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
    # Properties
    # ==================================================

    @property
    def items_count(self):

        return self.items.count()

    @property
    def total_items(self):

        return sum(
            (
                item.quantity
                for item in self.items.all()
            ),
            0,
        )

    @property
    def packages_count(self):

        return self.packages.count()

    @property
    def has_packages(self):

        return self.packages.exists()

    @property
    def is_ready_for_dispatch(self):

        return (
            self.status
            == self.Status.READY_FOR_DISPATCH
        )

    @property
    def is_dispatched(self):

        return self.status in [
            self.Status.DISPATCHED,
            self.Status.OUT_FOR_DELIVERY,
            self.Status.DELIVERED,
        ]

    @property
    def is_delivered(self):

        return (
            self.status
            == self.Status.DELIVERED
        )

    @property
    def is_cancelled(self):

        return (
            self.status
            == self.Status.CANCELLED
        )

    @property
    def is_terminal(self):

        return self.status in [
            self.Status.DELIVERED,
            self.Status.CANCELLED,
            self.Status.FAILED,
        ]