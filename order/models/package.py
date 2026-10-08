from decimal import Decimal

import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
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
    """

    class PackageType(models.TextChoices):

        ENVELOPE = ("envelope", "Envelope")
        SMALL_BOX = ("small_box", "Small Box")
        MEDIUM_BOX = ("medium_box", "Medium Box")
        LARGE_BOX = ("large_box", "Large Box")
        CUSTOM = ("custom", "Custom")

    class Status(models.TextChoices):

        CREATED = ("created", "Created")
        PACKING = ("packing", "Packing")
        PACKED = ("packed", "Packed")
        READY_FOR_PICKUP = ("ready_for_pickup", "Ready for Pickup")
        PICKED_UP = ("picked_up", "Picked Up")
        IN_TRANSIT = ("in_transit", "In Transit")
        DELIVERED = ("delivered", "Delivered")
        CANCELLED = ("cancelled", "Cancelled")
        LOST = ("lost", "Lost")
        DAMAGED = ("damaged", "Damaged")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    fulfillment = models.ForeignKey(
        "order.OrderFulfillment",
        on_delete=models.PROTECT,
        related_name="packages",
    )

    package_number = models.CharField(
        max_length=50,
        unique=True,
        editable=False,
        db_index=True,
    )

    tracking_number = models.CharField(
        max_length=100,
        unique=True,
        editable=False,
        db_index=True,
    )

    package_type = models.CharField(
        max_length=30,
        choices=PackageType.choices,
        default=PackageType.CUSTOM,
    )

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
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="Weight in kilograms.",
    )

    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Length in centimeters.",
    )

    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Width in centimeters.",
    )

    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
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
        validators=[MinValueValidator(Decimal("0.00"))],
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

        ordering = ["created_at"]

        indexes = [
            models.Index(
                fields=["status"],
                name="package_status_idx",
            ),
            models.Index(
                fields=["fulfillment", "status"],
                name="package_fulfillment_status_idx",
            ),
            models.Index(
                fields=["created_at"],
                name="package_created_idx",
            ),
        ]

    def __str__(self):

        return f"Package {self.package_number}"

    def clean(self):

        if self.fulfillment_id is None:

            raise ValidationError(
                {
                    "fulfillment": (
                        "A package must belong to an "
                        "order fulfillment."
                    )
                }
            )

        if (
            self.requires_special_handling
            and not self.special_handling_note.strip()
        ):

            raise ValidationError(
                {
                    "special_handling_note": (
                        "A special handling note is "
                        "required when special handling "
                        "is enabled."
                    )
                }
            )

        # --------------------------------------------------
        # Status timestamp requirements
        # --------------------------------------------------

        status_requirements = {
            self.Status.PACKED: "packed_at",
            self.Status.READY_FOR_PICKUP: "ready_for_pickup_at",
            self.Status.PICKED_UP: "picked_up_at",
            self.Status.IN_TRANSIT: "in_transit_at",
            self.Status.DELIVERED: "delivered_at",
            self.Status.CANCELLED: "cancelled_at",
        }

        required_field = status_requirements.get(self.status)

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

    def save(self, *args, **kwargs):

        if not self.package_number:

            self.package_number = (
                f"PKG-{uuid.uuid4().hex[:12].upper()}"
            )

        if not self.tracking_number:

            self.tracking_number = (
                f"TRK-{uuid.uuid4().hex[:14].upper()}"
            )

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
    def volume_cm3(self):

        return self.length * self.width * self.height

    @property
    def is_ready_for_pickup(self):

        return self.status == self.Status.READY_FOR_PICKUP

    @property
    def is_picked_up(self):

        return self.status in [
            self.Status.PICKED_UP,
            self.Status.IN_TRANSIT,
            self.Status.DELIVERED,
        ]

    @property
    def is_in_transit(self):

        return self.status == self.Status.IN_TRANSIT

    @property
    def is_delivered(self):

        return self.status == self.Status.DELIVERED

    @property
    def is_cancelled(self):

        return self.status == self.Status.CANCELLED

    @property
    def is_terminal(self):

        return self.status in [
            self.Status.DELIVERED,
            self.Status.CANCELLED,
            self.Status.LOST,
            self.Status.DAMAGED,
        ]

    @property
    def item_quantity(self):

        return sum(
            item.quantity for item in self.items.all()
        )


class PackageItem(models.Model):
    """
    Link between a Package and an OrderItem.

    A package may contain quantities of one or more order
    items. An order item may be split across packages.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    package = models.ForeignKey(
        "order.Package",
        on_delete=models.CASCADE,
        related_name="items",
    )

    order_item = models.ForeignKey(
        "order.OrderItem",
        on_delete=models.PROTECT,
        related_name="package_items",
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=["package", "order_item"],
                name="unique_package_order_item",
            ),
        ]

        indexes = [
            models.Index(fields=["order_item"]),
        ]

    def clean(self):

        if self.package_id is None:

            raise ValidationError(
                {"package": "Package is required."}
            )

        if self.order_item_id is None:

            raise ValidationError(
                {"order_item": "Order item is required."}
            )

        if (
            self.package.fulfillment_id
            != self.order_item.fulfillment_id
        ):

            raise ValidationError(
                {
                    "order_item": (
                        "Order item must belong to the "
                        "package fulfillment."
                    )
                }
            )

    def save(self, *args, **kwargs):

        if self._state.adding or kwargs.pop(
            "full_clean",
            False,
        ):
            self.full_clean()

        super().save(*args, **kwargs)