import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class OrderAddress(models.Model):
    """
    Address snapshot attached to an order.

    The address is copied at checkout so that changes to the user's
    saved address later do not modify historical order records.
    """

    class AddressType(models.TextChoices):
        SHIPPING = "SHIPPING", "Shipping"
        BILLING = "BILLING", "Billing"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    order = models.ForeignKey(
        "order.Order",
        on_delete=models.CASCADE,
        related_name="addresses",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="order_addresses",
    )

    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices,
        default=AddressType.SHIPPING,
    )

    recipient_name = models.CharField(
        max_length=150,
    )

    phone_number = models.CharField(
        max_length=30,
    )

    address_line_1 = models.CharField(
        max_length=255,
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
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
    )

    landmark = models.CharField(
        max_length=255,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
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
        db_table = "order_addresses"

        constraints = [
            models.UniqueConstraint(
                fields=["order", "address_type"],
                name="unique_order_address_type",
            ),
        ]

        indexes = [
            models.Index(
                fields=["order"],
                name="order_address_order_idx",
            ),
            models.Index(
                fields=["user"],
                name="order_address_user_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.address_type} address "
            f"for order {self.order_id}"
        )

    def clean(self):
        if self.address_type not in dict(
            self.AddressType.choices
        ):
            raise ValidationError(
                {"address_type": "Invalid address type."}
            )

        if self.latitude is not None:
            if not -90 <= self.latitude <= 90:
                raise ValidationError(
                    {"latitude": "Latitude must be between -90 and 90."}
                )

        if self.longitude is not None:
            if not -180 <= self.longitude <= 180:
                raise ValidationError(
                    {"longitude": "Longitude must be between -180 and 180."}
                )