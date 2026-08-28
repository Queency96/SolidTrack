from decimal import Decimal
import uuid

from django.core.exceptions import ValidationError
from django.db import models


class OrderItem(models.Model):
    """
    Historical snapshot of one product or product variant
    purchased in an Order.

    Each OrderItem belongs to exactly one Order.

    After checkout grouping, each OrderItem also belongs
    to one OrderFulfillment.

    The fulfillment determines which physical VendorStore
    is responsible for preparing and handing the item to
    a rider.
    """

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
        on_delete=models.CASCADE,
        related_name="items",
    )

    # ==================================================
    # Fulfillment
    # ==================================================

    fulfillment = models.ForeignKey(
        "order.OrderFulfillment",
        on_delete=models.PROTECT,
        related_name="items",
        null=True,
        blank=True,
    )

    # ==================================================
    # Product References
    # ==================================================

    product = models.ForeignKey(
        "vendors.Product",
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    variant = models.ForeignKey(
        "vendors.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items",
        null=True,
        blank=True,
    )

    # ==================================================
    # Store Reference
    # ==================================================

    store = models.ForeignKey(
        "vendors.VendorStore",
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    # ==================================================
    # Product Snapshot
    # ==================================================

    product_name = models.CharField(
        max_length=255,
    )

    product_sku = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # ==================================================
    # Variant Snapshot
    # ==================================================

    variant_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    variant_sku = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    option_summary = models.CharField(
        max_length=1000,
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

    # ==================================================
    # Pricing
    # ==================================================

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    # ==================================================
    # Currency
    # ==================================================

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    # ==================================================
    # Timestamp
    # ==================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
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
                    "order",
                ],
            ),

            models.Index(
                fields=[
                    "fulfillment",
                ],
            ),

            models.Index(
                fields=[
                    "product",
                ],
            ),

            models.Index(
                fields=[
                    "variant",
                ],
            ),

            models.Index(
                fields=[
                    "store",
                ],
            ),

            models.Index(
                fields=[
                    "order",
                    "store",
                ],
            ),

            models.Index(
                fields=[
                    "order",
                    "fulfillment",
                ],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return (
            f"{self.product_name}"
            f"{' - ' + self.variant_name if self.variant_name else ''}"
            f" x {self.quantity}"
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
                        "An order item must "
                        "belong to an order."
                    )
                }
            )

        # ----------------------------------------------
        # Product
        # ----------------------------------------------

        if self.product_id is None:

            raise ValidationError(
                {
                    "product": (
                        "An order item must "
                        "reference a product."
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
                        "An order item must "
                        "reference a pickup store."
                    )
                }
            )

        # ----------------------------------------------
        # Product → Store
        # ----------------------------------------------

        if (
            self.product.store_id
            != self.store_id
        ):

            raise ValidationError(
                {
                    "store": (
                        "The selected store does "
                        "not match the product's "
                        "store."
                    )
                }
            )

        # ----------------------------------------------
        # Variant ownership
        # ----------------------------------------------

        if self.variant_id is not None:

            if (
                self.variant.product_id
                != self.product_id
            ):

                raise ValidationError(
                    {
                        "variant": (
                            "The selected variant "
                            "does not belong to "
                            "the selected product."
                        )
                    }
                )

        # ----------------------------------------------
        # Fulfillment ownership
        # ----------------------------------------------

        if self.fulfillment_id is not None:

            if (
                self.fulfillment.order_id
                != self.order_id
            ):

                raise ValidationError(
                    {
                        "fulfillment": (
                            "The fulfillment does "
                            "not belong to this order."
                        )
                    }
                )

            if (
                self.fulfillment.store_id
                != self.store_id
            ):

                raise ValidationError(
                    {
                        "fulfillment": (
                            "The fulfillment store "
                            "does not match the "
                            "item's store."
                        )
                    }
                )

        # ----------------------------------------------
        # Quantity
        # ----------------------------------------------

        if self.quantity <= 0:

            raise ValidationError(
                {
                    "quantity": (
                        "Quantity must be "
                        "greater than zero."
                    )
                }
            )

        # ----------------------------------------------
        # Unit price
        # ----------------------------------------------

        if self.unit_price < Decimal("0.00"):

            raise ValidationError(
                {
                    "unit_price": (
                        "Unit price cannot "
                        "be negative."
                    )
                }
            )

        # ----------------------------------------------
        # Subtotal
        # ----------------------------------------------

        calculated_subtotal = (
            self.unit_price
            * Decimal(
                str(self.quantity),
            )
        )

        if self.subtotal != calculated_subtotal:

            raise ValidationError(
                {
                    "subtotal": (
                        "Item subtotal does not "
                        "match unit price multiplied "
                        "by quantity."
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
    def has_variant(self):

        return self.variant_id is not None

    @property
    def display_name(self):

        if self.variant_name:

            return (
                f"{self.product_name} - "
                f"{self.option_summary or self.variant_name}"
            )

        return self.product_name

    @property
    def sku(self):

        if self.variant_sku:

            return self.variant_sku

        return self.product_sku

    @property
    def pickup_location(self):

        return {
            "latitude": self.store_latitude,
            "longitude": self.store_longitude,
        }

    @property
    def pickup_address(self):

        parts = [
            self.store_address_line_1,
            self.store_address_line_2,
            self.store_city,
            self.store_state,
            self.store_country,
            self.store_postal_code,
        ]

        return ", ".join(
            part
            for part in parts
            if part
        )