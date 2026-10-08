from decimal import Decimal

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from riders.models import RiderProfile


class OrderFulfillment(models.Model):
    """
    Represents the fulfillment of an Order by one VendorStore.

    An Order may have multiple fulfillments when the
    customer purchases from multiple stores.

    Delivery inputs
    ---------------
    The following fields are the fulfillment-level inputs to
    DeliveryService.create_delivery:

        package_size
        delivery_type
        vehicle_type
        scheduled_at

    They are captured at checkout time and passed through
    unchanged when OrderFulfillmentService.mark_ready_for_dispatch
    delegates delivery creation.

    Snapshot policy
    ---------------
    Store fields and delivery-destination fields are
    snapshotted at checkout. Later edits to the store or
    customer address do not affect historical fulfillments.
    """

    # ==================================================
    # Status
    # ==================================================

    class Status(models.TextChoices):

        PENDING = ("pending", "Pending")
        PROCESSING = ("processing", "Processing")
        PACKING = ("packing", "Packing")
        READY_FOR_DISPATCH = ("ready_for_dispatch", "Ready for Dispatch")
        DISPATCHED = ("dispatched", "Dispatched")
        OUT_FOR_DELIVERY = ("out_for_delivery", "Out for Delivery")
        DELIVERED = ("delivered", "Delivered")
        CANCELLED = ("cancelled", "Cancelled")
        FAILED = ("failed", "Failed")

    # ==================================================
    # Delivery inputs
    # ==================================================

    class PackageSize(models.TextChoices):

        SMALL = ("SMALL", "Small")
        MEDIUM = ("MEDIUM", "Medium")
        LARGE = ("LARGE", "Large")

    class DeliveryType(models.TextChoices):

        INSTANT = ("INSTANT", "Instant")
        SCHEDULED = ("SCHEDULED", "Scheduled")

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

    store_contact_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    store_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
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

    store_pickup_instructions = models.TextField(
        blank=True,
        default="",
    )

    store_preparation_time_minutes = models.PositiveIntegerField(
        default=0,
    )

    # ==================================================
    # Delivery Destination Snapshot
    # ==================================================

    delivery_contact_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    delivery_contact_phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    delivery_address_line_1 = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    delivery_address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    delivery_city = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    delivery_state = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    delivery_country = models.CharField(
        max_length=100,
        blank=True,
        default="Nigeria",
    )

    delivery_postal_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    delivery_latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    delivery_longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    delivery_instructions = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Delivery OTP
    # ==================================================

    delivery_otp = models.CharField(
        max_length=6,
        blank=True,
        default="",
        db_index=True,
        help_text=(
            "6-digit code the customer shares with the rider "
            "to confirm handover."
        ),
    )

    delivery_otp_generated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivery_otp_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    delivery_otp_attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text="Failed verification attempts. Locks after 5.",
    )


    # ==================================================
    # Delivery inputs (O1-A + O3-B)
    # ==================================================

    package_size = models.CharField(
        max_length=10,
        choices=PackageSize.choices,
        default=PackageSize.SMALL,
        help_text=(
            "Package size bucket used for delivery pricing."
        ),
    )

    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
        default=DeliveryType.INSTANT,
        help_text=(
            "Delivery type for the associated Delivery."
        ),
    )

    vehicle_type = models.CharField(
        max_length=20,
        choices=RiderProfile.VehicleType.choices,
        null=True,
        blank=True,
        help_text=(
            "Requested vehicle class. "
            "Null means the dispatcher decides."
        ),
    )

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Required when delivery_type is SCHEDULED."
        ),
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

        ordering = ["created_at"]

        constraints = [

            models.UniqueConstraint(
                fields=["order", "store"],
                name="unique_order_store_fulfillment",
            ),
        ]

        indexes = [

            models.Index(
                fields=["order", "status"],
            ),

            models.Index(
                fields=["store", "status"],
            ),

            models.Index(
                fields=["status"],
            ),

            models.Index(
                fields=["created_at"],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return (
            f"Fulfillment {self.id} - "
            f"{self.store_name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        # ----------------------------------------------
        # Required references
        # ----------------------------------------------

        if self.order_id is None:

            raise ValidationError(
                {
                    "order": (
                        "A fulfillment must belong "
                        "to an order."
                    )
                }
            )

        if self.store_id is None:

            raise ValidationError(
                {
                    "store": (
                        "A fulfillment must belong "
                        "to a store."
                    )
                }
            )

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

            if (
                getattr(self, field_name)
                < Decimal("0.00")
            ):

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
            calculated_total = Decimal("0.00")

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
        # Delivery inputs
        # ----------------------------------------------

        if (
            self.delivery_type
            == self.DeliveryType.SCHEDULED
            and self.scheduled_at is None
        ):

            raise ValidationError(
                {
                    "scheduled_at": (
                        "Scheduled delivery requires "
                        "a scheduled date and time."
                    )
                }
            )

        if (
            self.delivery_type
            == self.DeliveryType.INSTANT
            and self.scheduled_at is not None
        ):

            raise ValidationError(
                {
                    "scheduled_at": (
                        "Instant delivery must not "
                        "have a scheduled time."
                    )
                }
            )

        # ----------------------------------------------
        # Status timestamps
        # ----------------------------------------------

        timestamp_requirements = {
            self.Status.PROCESSING: "processing_at",
            self.Status.PACKING: "packing_at",
            self.Status.READY_FOR_DISPATCH: "ready_for_dispatch_at",
            self.Status.DISPATCHED: "dispatched_at",
            self.Status.DELIVERED: "delivered_at",
            self.Status.CANCELLED: "cancelled_at",
        }

        required_field = timestamp_requirements.get(
            self.status,
        )

        if (
            required_field
            and getattr(self, required_field) is None
        ):

            raise ValidationError(
                {
                    required_field: (
                        f"{required_field.replace('_', ' ').capitalize()} "
                        f"is required when status is "
                        f"{self.status}."
                    )
                }
            )

    # ==================================================
    # Save
    # ==================================================

    def save(self, *args, **kwargs):

        if self._state.adding or kwargs.pop(
            "full_clean",
            False,
        ):
            self.full_clean()

        super().save(*args, **kwargs)

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
    def is_failed(self):

        return (
            self.status
            == self.Status.FAILED
        )

    @property
    def is_terminal(self):

        return self.status in [
            self.Status.DELIVERED,
            self.Status.CANCELLED,
            self.Status.FAILED,
        ]