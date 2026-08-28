from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError
from django.db import models
from common.models import TimeStampedModel


class Package(TimeStampedModel):
    """
    Represents one physical package prepared by a VendorStore
    for an OrderFulfillment.

    A Package is a physical logistics unit.

    It is different from an OrderItem:

        OrderItem
            = what the customer purchased

        Package
            = physical parcel containing one or more items

    One OrderFulfillment may contain multiple Packages.

    Example:

        Order
          │
          └── OrderFulfillment
                  │
                  ├── Package A
                  ├── Package B
                  └── Package C
    """

    # ==================================================
    # Package Type
    # ==================================================

    class PackageType(models.TextChoices):

        ENVELOPE = (
            "envelope",
            "Envelope",
        )

        SMALL_BOX = (
            "small_box",
            "Small Box",
        )

        MEDIUM_BOX = (
            "medium_box",
            "Medium Box",
        )

        LARGE_BOX = (
            "large_box",
            "Large Box",
        )

        CUSTOM = (
            "custom",
            "Custom",
        )

    # ==================================================
    # Package Status
    # ==================================================

    class Status(models.TextChoices):

        CREATED = (
            "created",
            "Created",
        )

        PACKING = (
            "packing",
            "Packing",
        )

        PACKED = (
            "packed",
            "Packed",
        )

        READY_FOR_PICKUP = (
            "ready_for_pickup",
            "Ready for Pickup",
        )

        PICKED_UP = (
            "picked_up",
            "Picked Up",
        )

        IN_TRANSIT = (
            "in_transit",
            "In Transit",
        )

        DELIVERED = (
            "delivered",
            "Delivered",
        )

        CANCELLED = (
            "cancelled",
            "Cancelled",
        )

        LOST = (
            "lost",
            "Lost",
        )

        DAMAGED = (
            "damaged",
            "Damaged",
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
    # Fulfillment
    # ==================================================

    fulfillment = models.ForeignKey(
        "order.OrderFulfillment",
        on_delete=models.PROTECT,
        related_name="packages",
    )

    # ==================================================
    # Package Number
    # ==================================================

    package_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        db_index=True,
    )

    # ==================================================
    # Tracking
    # ==================================================

    tracking_number = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        db_index=True,
    )

    # ==================================================
    # Package Type
    # ==================================================

    package_type = models.CharField(
        max_length=30,
        choices=PackageType.choices,
        default=PackageType.CUSTOM,
    )

    # ==================================================
    # Status
    # ==================================================

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
    )

    # ==================================================
    # Physical Properties
    # ==================================================

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Weight in kilograms.",
    )

    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Length in centimeters.",
    )

    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Width in centimeters.",
    )

    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Height in centimeters.",
    )

    # ==================================================
    # Package Characteristics
    # ==================================================

    is_fragile = models.BooleanField(
        default=False,
    )

    requires_special_handling = models.BooleanField(
        default=False,
    )

    special_handling_note = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Package Value
    # ==================================================

    declared_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    # ==================================================
    # Description
    # ==================================================

    description = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    # ==================================================
    # Packaging Information
    # ==================================================

    packaging_note = models.TextField(
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

    packed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    ready_for_pickup_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    picked_up_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    in_transit_at = models.DateTimeField(
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
            "created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "fulfillment",
                ],
                name="package_fulfillment_idx",
            ),

            models.Index(
                fields=[
                    "status",
                ],
                name="package_status_idx",
            ),

            models.Index(
                fields=[
                    "fulfillment",
                    "status",
                ],
                name="package_fulfillment_status_idx",
            ),

            models.Index(
                fields=[
                    "tracking_number",
                ],
                name="package_tracking_idx",
            ),

            models.Index(
                fields=[
                    "created_at",
                ],
                name="package_created_idx",
            ),

        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return (
            f"Package "
            f"{self.package_number}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        # ----------------------------------------------
        # Fulfillment
        # ----------------------------------------------

        if self.fulfillment_id is None:

            raise ValidationError(
                {
                    "fulfillment": (
                        "A package must belong "
                        "to an order fulfillment."
                    )
                }
            )

        # ----------------------------------------------
        # Weight
        # ----------------------------------------------

        if self.weight < Decimal("0.000"):

            raise ValidationError(
                {
                    "weight": (
                        "Package weight cannot "
                        "be negative."
                    )
                }
            )

        # ----------------------------------------------
        # Dimensions
        # ----------------------------------------------

        dimension_fields = [
            "length",
            "width",
            "height",
        ]

        for field_name in dimension_fields:

            value = getattr(
                self,
                field_name,
            )

            if value < Decimal("0.00"):

                raise ValidationError(
                    {
                        field_name: (
                            f"{field_name.capitalize()} "
                            "cannot be negative."
                        )
                    }
                )

        # ----------------------------------------------
        # Declared Value
        # ----------------------------------------------

        if (
            self.declared_value
            < Decimal("0.00")
        ):

            raise ValidationError(
                {
                    "declared_value": (
                        "Declared value cannot "
                        "be negative."
                    )
                }
            )

        # ----------------------------------------------
        # Special Handling
        # ----------------------------------------------

        if (
            self.requires_special_handling
            and not self.special_handling_note.strip()
        ):

            raise ValidationError(
                {
                    "special_handling_note": (
                        "A special handling note "
                        "is required when special "
                        "handling is enabled."
                    )
                }
            )

        # ----------------------------------------------
        # Status Timestamps
        # ----------------------------------------------

        if (
            self.status == self.Status.PACKED
            and self.packed_at is None
        ):

            raise ValidationError(
                {
                    "packed_at": (
                        "Packed timestamp is "
                        "required."
                    )
                }
            )

        if (
            self.status
            == self.Status.READY_FOR_PICKUP
            and self.ready_for_pickup_at is None
        ):

            raise ValidationError(
                {
                    "ready_for_pickup_at": (
                        "Ready-for-pickup timestamp "
                        "is required."
                    )
                }
            )

        if (
            self.status == self.Status.PICKED_UP
            and self.picked_up_at is None
        ):

            raise ValidationError(
                {
                    "picked_up_at": (
                        "Picked-up timestamp is "
                        "required."
                    )
                }
            )

        if (
            self.status == self.Status.IN_TRANSIT
            and self.in_transit_at is None
        ):

            raise ValidationError(
                {
                    "in_transit_at": (
                        "In-transit timestamp is "
                        "required."
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
                        "Delivered timestamp is "
                        "required."
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
                        "Cancelled timestamp is "
                        "required."
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

        if not self.package_number:

            self.package_number = (
                f"PKG-"
                f"{uuid.uuid4().hex[:12].upper()}"
            )

        if not self.tracking_number:

            self.tracking_number = (
                f"TRK-"
                f"{uuid.uuid4().hex[:14].upper()}"
            )

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    # ==================================================
    # Properties
    # ==================================================

    @property
    def volume_cm3(self):

        return (
            self.length
            * self.width
            * self.height
        )

    @property
    def is_ready_for_pickup(self):

        return (
            self.status
            == self.Status.READY_FOR_PICKUP
        )

    @property
    def is_picked_up(self):

        return self.status in [
            self.Status.PICKED_UP,
            self.Status.IN_TRANSIT,
            self.Status.DELIVERED,
        ]

    @property
    def is_in_transit(self):

        return (
            self.status
            == self.Status.IN_TRANSIT
        )

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
            self.Status.LOST,
            self.Status.DAMAGED,
        ]