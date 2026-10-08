from decimal import Decimal

import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from common.models import TimeStampedModel


class DeliveryItem(TimeStampedModel):
    """
    Product item included in a delivery.

    A delivery may contain multiple products and/or
    multiple variants of the same product.

    Product information is linked to the vendor's
    catalog, while important commercial values are
    stored as snapshots so historical deliveries remain
    accurate even if the product changes later.
    """

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
        related_name="items",
    )

    # ==================================================
    # Product
    # ==================================================

    product = models.ForeignKey(
        "vendors.Product",
        on_delete=models.PROTECT,
        related_name="delivery_items",
    )

    # ==================================================
    # Product Variant
    # ==================================================

    variant = models.ForeignKey(
        "vendors.ProductVariant",
        on_delete=models.PROTECT,
        related_name="delivery_items",
        null=True,
        blank=True,
    )

    # ==================================================
    # Store
    # ==================================================
    #
    # Store is kept explicitly because a vendor can have
    # multiple stores and the order must identify the
    # exact store from which the rider will collect the
    # products.
    #
    # This should normally correspond to:
    #
    #     product.store
    #
    # ==================================================

    store = models.ForeignKey(
        "vendors.VendorStore",
        on_delete=models.PROTECT,
        related_name="delivery_items",
    )

    # ==================================================
    # Product Snapshot
    # ==================================================
    #
    # These values preserve what the customer actually
    # ordered even if the product is later edited.
    #

    product_name = models.CharField(
        max_length=255,
    )

    variant_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # ==================================================
    # Quantity
    # ==================================================

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
        ],
    )

    # ==================================================
    # Pricing Snapshot
    # ==================================================

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ==================================================
    # Weight
    # ==================================================

    unit_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
    )

    total_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
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
                fields=["delivery"],
            ),

            models.Index(
                fields=["product"],
            ),

            models.Index(
                fields=["variant"],
            ),

            models.Index(
                fields=["store"],
            ),
        ]

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        if (
            self.unit_price is not None
            and self.unit_price < Decimal("0.00")
        ):

            raise ValidationError(
                {
                    "unit_price": (
                        "Unit price cannot be negative."
                    )
                }
            )

        if (
            self.unit_weight is not None
            and self.unit_weight < Decimal("0.000")
        ):

            raise ValidationError(
                {
                    "unit_weight": (
                        "Unit weight cannot be negative."
                    )
                }
            )

    # ==================================================
    # Save
    # ==================================================

    def save(self, *args, **kwargs):

        # --------------------------------------------------
        # Recompute totals from unit values.
        #
        # These fields are derived and should not be set
        # independently by callers.
        # --------------------------------------------------

        self.total_price = (
            self.unit_price
            * Decimal(self.quantity)
        ).quantize(Decimal("0.01"))

        if self.unit_weight is not None:

            self.total_weight = (
                self.unit_weight
                * Decimal(self.quantity)
            ).quantize(Decimal("0.001"))

        else:

            self.total_weight = None

        if self._state.adding or kwargs.pop(
            "full_clean",
            False,
        ):
            self.full_clean()

        super().save(*args, **kwargs)

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return (
            f"{self.product_name} "
            f"x {self.quantity}"
        )