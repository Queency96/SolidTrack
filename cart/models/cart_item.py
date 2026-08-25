from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models


class CartItem(models.Model):
    """
    Represents a product or product variant inside
    a customer's shopping cart.

    A CartItem always belongs to one Cart.

    A product can be purchased directly when it has
    no variants, or through a specific ProductVariant
    when variants exist.

    The unit_price is a snapshot of the price at the
    time the item is added to the cart.
    """

    # ==================================================
    # Cart
    # ==================================================

    cart = models.ForeignKey(
        "orders.Cart",
        on_delete=models.CASCADE,
        related_name="items",
    )

    # ==================================================
    # Product
    # ==================================================

    product = models.ForeignKey(
        "vendors.Product",
        on_delete=models.PROTECT,
        related_name="cart_items",
    )

    # ==================================================
    # Variant
    # ==================================================

    variant = models.ForeignKey(
        "vendors.ProductVariant",
        on_delete=models.PROTECT,
        related_name="cart_items",
        null=True,
        blank=True,
    )

    # ==================================================
    # Quantity
    # ==================================================

    quantity = models.PositiveIntegerField(
        default=1,
    )

    # ==================================================
    # Price Snapshot
    # ==================================================

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # ==================================================
    # Timestamp
    # ==================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "created_at",
        ]

        constraints = [

            # ------------------------------------------
            # Product without variant
            # ------------------------------------------

            models.UniqueConstraint(
                fields=[
                    "cart",
                    "product",
                    'variant',
                ],
                condition=models.Q(
                    variant__isnull=True,
                ),
                name=(
                    "unique_product_variant_per_cart_item"
                ),
            ),

            # ------------------------------------------
            # Product variant
            # ------------------------------------------

            models.UniqueConstraint(
                fields=[
                    "cart",
                    "variant",
                ],
                condition=models.Q(
                    variant__isnull=False,
                ),
                name=(
                    "unique_variant_cart_item"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "cart",
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
                    "cart",
                    "product",
                ],
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        item_name = self.display_name

        return (
            f"{item_name} "
            f"x {self.quantity}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate cart item configuration.
        """

        # ----------------------------------------------
        # Cart
        # ----------------------------------------------

        if self.cart_id is None:

            raise ValidationError(
                {
                    "cart": (
                        "A cart item must "
                        "belong to a cart."
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
                        "A cart item must "
                        "reference a product."
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
        # Cart status
        # ----------------------------------------------

        if not self.cart.is_active:

            raise ValidationError(
                {
                    "cart": (
                        "Items cannot be added "
                        "to an inactive cart."
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

            # ------------------------------------------
            # Variant availability
            # ------------------------------------------

            if not self.variant.is_available:

                raise ValidationError(
                    {
                        "variant": (
                            "The selected variant "
                            "is not available."
                        )
                    }
                )

            # ------------------------------------------
            # Variant inventory
            # ------------------------------------------

            if (
                self.variant.track_inventory
                and self.quantity
                > self.variant.stock_quantity
            ):

                raise ValidationError(
                    {
                        "quantity": (
                            "Insufficient stock "
                            "for the selected "
                            "variant."
                        )
                    }
                )

        else:

            # ------------------------------------------
            # Product availability
            # ------------------------------------------

            if not self.product.is_available:

                raise ValidationError(
                    {
                        "product": (
                            "Product is not "
                            "available."
                        )
                    }
                )

            # ------------------------------------------
            # Product inventory
            # ------------------------------------------

            if (
                self.product.track_inventory
                and self.quantity
                > self.product.stock_quantity
            ):

                raise ValidationError(
                    {
                        "quantity": (
                            "Insufficient "
                            "product stock."
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
        """
        Save the cart item.

        Price is only populated automatically when
        creating a new CartItem.

        Existing price snapshots are preserved.
        """

        is_new = self.pk is None

        # ----------------------------------------------
        # Price snapshot
        # ----------------------------------------------

        if is_new:

            self.unit_price = (
                self.effective_price
            )

        # ----------------------------------------------
        # Validation
        # ----------------------------------------------

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    # ==================================================
    # Effective Price
    # ==================================================

    @property
    def effective_price(self):
        """
        Return the current price that should be used
        when initially creating this cart item.

        Variant price takes precedence over product
        price.
        """

        if self.variant is not None:

            return self.variant.effective_price

        return self.product.price

    # ==================================================
    # Subtotal
    # ==================================================

    @property
    def subtotal(self):
        """
        Return the cart item's subtotal.

        Uses the stored unit_price snapshot.
        """

        return (
            self.unit_price
            * Decimal(
                str(self.quantity),
            )
        )

    # ==================================================
    # Display Name
    # ==================================================

    @property
    def display_name(self):
        """
        Return the name that should be displayed
        to the customer.
        """

        if self.variant is not None:

            if self.variant.option_summary:

                return (
                    f"{self.product.name} - "
                    f"{self.variant.option_summary}"
                )

            return self.variant.name

        return self.product.name

    # ==================================================
    # SKU
    # ==================================================

    @property
    def sku(self):
        """
        Return the most specific SKU available.
        """

        if (
            self.variant is not None
            and self.variant.sku
        ):

            return self.variant.sku

        return self.product.sku

    # ==================================================
    # Stock Tracking
    # ==================================================

    @property
    def tracks_inventory(self):
        """
        Determine whether this cart item tracks
        inventory.
        """

        if self.variant is not None:

            return self.variant.track_inventory

        return self.product.track_inventory

    # ==================================================
    # Available Stock
    # ==================================================

    @property
    def available_stock(self):
        """
        Return the currently available stock.

        Returns None when inventory tracking is
        disabled.
        """

        if not self.tracks_inventory:

            return None

        if self.variant is not None:

            return self.variant.stock_quantity

        return self.product.stock_quantity

    # ==================================================
    # Stock Validity
    # ==================================================

    @property
    def has_sufficient_stock(self):
        """
        Determine whether the current quantity can
        still be fulfilled.
        """

        if not self.tracks_inventory:

            return True

        return (
            self.quantity
            <= self.available_stock
        )

    # ==================================================
    # Availability
    # ==================================================

    @property
    def is_available(self):
        """
        Determine whether the cart item can currently
        be purchased.
        """

        if self.variant is not None:

            return (
                self.variant.is_available
                and self.has_sufficient_stock
            )

        return (
            self.product.is_available
            and self.has_sufficient_stock
        )

    # ==================================================
    # Variant
    # ==================================================

    @property
    def has_variant(self):
        """
        Determine whether this cart item represents
        a specific product variant.
        """

        return self.variant_id is not None

    # ==================================================
    # Product Image
    # ==================================================

    @property
    def primary_image(self):
        """
        Return the most appropriate primary image.

        Variant image takes precedence over the general
        product image.
        """

        if self.variant is not None:

            image = (
                self.variant.images
                .filter(
                    is_primary=True,
                    is_active=True,
                )
                .first()
            )

            if image is not None:

                return image

        return (
            self.product.images
            .filter(
                is_primary=True,
                is_active=True,
            )
            .first()
        )
