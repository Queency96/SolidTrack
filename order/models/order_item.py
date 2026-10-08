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

    Line-item lifecycle
    -------------------
    `fulfillment_status` tracks each line independently so a
    vendor can ship some items and mark others unavailable:

        PENDING      — not yet processed by the vendor
        FULFILLED    — vendor will ship this line
        UNAVAILABLE  — vendor cannot ship this line

    Perishable items marked UNAVAILABLE are not refunded.

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
    # Perishable snapshot
    # ==================================================
    #
    # Snapshotted from Product.is_perishable at checkout.
    # Later changes to the parent product do not affect the
    # refund behaviour of this historical line.
    # ==================================================

    is_perishable = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Snapshot of Product.is_perishable at checkout. "
            "Perishable items are excluded from refunds."
        ),
    )

    # ==================================================
    # Line-item fulfillment status
    # ==================================================

    class FulfillmentStatus(models.TextChoices):

        PENDING = ("PENDING", "Pending")
        FULFILLED = ("FULFILLED", "Fulfilled")
        UNAVAILABLE = ("UNAVAILABLE", "Unavailable")

    fulfillment_status = models.CharField(
        max_length=20,
        choices=FulfillmentStatus.choices,
        default=FulfillmentStatus.PENDING,
        db_index=True,
    )

    unavailable_reason = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Populated when fulfillment_status is UNAVAILABLE."
        ),
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
    # Weight snapshot
    # ==================================================
    #
    # Snapshotted from ProductVariant.weight (preferred) or
    # Product.weight at checkout. Later changes to the
    # catalog do not affect the weight of this historical
    # line, and downstream packaging / delivery pricing is
    # stable across catalog edits.
    #
    # Null means the weight was not known at checkout.
    # ==================================================

    unit_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text=(
            "Unit weight in kilograms, snapshotted at "
            "checkout. Null when the source catalog item "
            "had no weight."
        ),
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
                    "fulfillment",
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
                    "fulfillment",
                    "fulfillment_status",
                    "is_perishable",
                ],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        variant_suffix = (
            f" - {self.variant_name}"
            if self.variant_name
            else ""
        )

        return (
            f"{self.product_name}"
            f"{variant_suffix}"
            f" x {self.quantity}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate cross-object invariants for this line item.

        Order items are historical snapshots, so most fields
        are write-once at checkout. The checks below guard
        against programming errors that would silently
        corrupt an order.
        """

        # ----------------------------------------------
        # Required references
        # ----------------------------------------------

        if self.order_id is None:

            raise ValidationError(
                {
                    "order": (
                        "An order item must belong "
                        "to an order."
                    )
                }
            )

        if self.product_id is None:

            raise ValidationError(
                {
                    "product": (
                        "An order item must reference "
                        "a product."
                    )
                }
            )

        if self.store_id is None:

            raise ValidationError(
                {
                    "store": (
                        "An order item must reference "
                        "a pickup store."
                    )
                }
            )

        # ----------------------------------------------
        # Store must match the product's store
        # ----------------------------------------------

        if self.product.store_id != self.store_id:

            raise ValidationError(
                {
                    "store": (
                        "The selected store does not "
                        "match the product's store."
                    )
                }
            )

        # ----------------------------------------------
        # Variant must belong to the product
        # ----------------------------------------------

        if self.variant_id is not None:

            if self.variant.product_id != self.product_id:

                raise ValidationError(
                    {
                        "variant": (
                            "The selected variant does "
                            "not belong to the selected "
                            "product."
                        )
                    }
                )

        # ----------------------------------------------
        # Fulfillment invariants
        # ----------------------------------------------

        if self.fulfillment_id is not None:

            if self.fulfillment.order_id != self.order_id:

                raise ValidationError(
                    {
                        "fulfillment": (
                            "The fulfillment does not "
                            "belong to this order."
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
                            "does not match the item's "
                            "store."
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
                        "Quantity must be greater "
                        "than zero."
                    )
                }
            )

        # ----------------------------------------------
        # Pricing
        # ----------------------------------------------

        if self.unit_price < Decimal("0.00"):

            raise ValidationError(
                {
                    "unit_price": (
                        "Unit price cannot be "
                        "negative."
                    )
                }
            )

        expected_subtotal = (
            self.unit_price * Decimal(self.quantity)
        ).quantize(Decimal("0.01"))

        if self.subtotal != expected_subtotal:

            raise ValidationError(
                {
                    "subtotal": (
                        "Item subtotal does not match "
                        "unit price multiplied by "
                        "quantity "
                        f"(expected {expected_subtotal})."
                    )
                }
            )

        # ----------------------------------------------
        # Weight
        # ----------------------------------------------

        if (
            self.unit_weight is not None
            and self.unit_weight < Decimal("0.000")
        ):

            raise ValidationError(
                {
                    "unit_weight": (
                        "Unit weight cannot be "
                        "negative."
                    )
                }
            )

        # ----------------------------------------------
        # Unavailable reason
        # ----------------------------------------------

        if (
            self.fulfillment_status
            == self.FulfillmentStatus.UNAVAILABLE
            and not self.unavailable_reason
        ):

            raise ValidationError(
                {
                    "unavailable_reason": (
                        "A reason is required when an "
                        "item is marked unavailable."
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
            "latitude": float(self.store_latitude),
            "longitude": float(self.store_longitude),
        }

    @property
    def is_refundable(self):
        """
        Whether this line contributes to a refund when the
        parent fulfillment fails.

        Perishable items are excluded per business policy.
        """

        return not self.is_perishable

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

    @property
    def is_unavailable(self):

        return (
            self.fulfillment_status
            == self.FulfillmentStatus.UNAVAILABLE
        )

    @property
    def is_fulfilled(self):

        return (
            self.fulfillment_status
            == self.FulfillmentStatus.FULFILLED
        )

    @property
    def total_weight(self):
        """
        Return the total line weight (unit * quantity), or
        None when unit weight is unknown.
        """

        if self.unit_weight is None:
            return None

        return (
            self.unit_weight * Decimal(self.quantity)
        ).quantize(Decimal("0.001"))