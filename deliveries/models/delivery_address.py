import uuid

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

from common.models import TimeStampedModel


class DeliveryAddress(TimeStampedModel):
    """
    Represents an operational address/contact point for a Delivery.

    A Delivery has exactly two addresses:

        PICKUP
            ↓
        VendorStore
            ↓
        DELIVERY
            ↓
        Customer

    The Delivery model itself keeps the coordinate and address
    snapshots used by pricing, routing and dispatch.

    DeliveryAddress keeps the contact information and detailed
    endpoint information used during the actual delivery.
    """

    # ==================================================
    # Address Type
    # ==================================================

    class AddressType(models.TextChoices):

        PICKUP = (
            "PICKUP",
            "Pickup",
        )

        DELIVERY = (
            "DELIVERY",
            "Delivery",
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
    # Delivery
    # ==================================================

    delivery = models.ForeignKey(
        "deliveries.Delivery",
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    # ==================================================
    # Address Type
    # ==================================================

    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices,
    )

    # ==================================================
    # Contact
    # ==================================================

    contact_name = models.CharField(
        max_length=255,
    )

    contact_phone = models.CharField(
        max_length=30,
    )

    # ==================================================
    # Address
    # ==================================================

    address_line_1 = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    city = models.CharField(
        max_length=100,
    )

    state = models.CharField(
        max_length=100,
    )

    country = models.CharField(
        max_length=100,
        default="Nigeria",
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    # ==================================================
    # Coordinates
    # ==================================================

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[
            MinValueValidator(Decimal("-90")),
            MaxValueValidator(Decimal("90")),
        ],
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[
            MinValueValidator(Decimal("-180")),
            MaxValueValidator(Decimal("180")),
        ],
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "address_type",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "delivery",
                    "address_type",
                ],
                name="unique_delivery_address_type",
            ),
        ]

        indexes = [

            models.Index(
                fields=[
                    "address_type",
                ],
            ),

            models.Index(
                fields=[
                    "delivery",
                    "address_type",
                ],
            ),

            models.Index(
                fields=[
                    "contact_phone",
                ],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return (
            f"{self.address_type} - "
            f"{self.contact_name} - "
            f"{self.city}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        # ----------------------------------------------
        # Delivery
        # ----------------------------------------------

        if self.delivery_id is None:

            raise ValidationError(
                {
                    "delivery": (
                        "A delivery address must "
                        "belong to a delivery."
                    )
                }
            )

        # ----------------------------------------------
        # Address Type
        # ----------------------------------------------

        if (
            self.address_type
            not in self.AddressType.values
        ):

            raise ValidationError(
                {
                    "address_type": (
                        "Invalid delivery "
                        "address type."
                    )
                }
            )

        # ----------------------------------------------
        # Contact Name
        # ----------------------------------------------

        if not (self.contact_name or "").strip():

            raise ValidationError(
                {
                    "contact_name": (
                        "Contact name is required."
                    )
                }
            )

        # ----------------------------------------------
        # Contact Phone
        # ----------------------------------------------

        if not (self.contact_phone or "").strip():

            raise ValidationError(
                {
                    "contact_phone": (
                        "Contact phone is required."
                    )
                }
            )

        # ----------------------------------------------
        # Address
        # ----------------------------------------------

        if not (self.address_line_1 or "").strip():

            raise ValidationError(
                {
                    "address_line_1": (
                        "Address line 1 is required."
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
    def full_address(self):

        parts = [
            self.address_line_1,
            self.address_line_2,
            self.city,
            self.state,
            self.country,
            self.postal_code,
        ]

        return ", ".join(
            part
            for part in parts
            if part
        )

    @property
    def location(self):

        return {
            "latitude": float(self.latitude),
            "longitude": float(self.longitude),
        }

    @property
    def is_pickup(self):

        return (
            self.address_type
            == self.AddressType.PICKUP
        )

    @property
    def is_delivery(self):

        return (
            self.address_type
            == self.AddressType.DELIVERY
        )