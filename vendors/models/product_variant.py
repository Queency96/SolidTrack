from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
import uuid



class ProductVariant(models.Model):
    """
    Represents a purchasable variation of a Product.

    Examples:

        T-Shirt
            ├── Black / Small
            ├── Black / Medium
            ├── Black / Large
            └── White / Medium

        iPhone
            ├── 128GB / Black
            ├── 256GB / Black
            └── 512GB / White

    Each variant maintains its own:

        • SKU
        • price
        • stock
        • weight
        • active status

    Variant option values are stored through
    ProductVariantOptionValue.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ==================================================
    # Product
    # ==================================================

    product = models.ForeignKey(
        "vendors.Product",
        on_delete=models.CASCADE,
        related_name="variants",
    )

    # ==================================================
    # Identity
    # ==================================================

    name = models.CharField(
        max_length=255,
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # ==================================================
    # Option Values
    # ==================================================

    option_values = models.ManyToManyField(
        "vendors.ProductOptionValue",
        through="vendors.ProductVariantOptionValue",
        related_name="variants",
        blank=True,
    )

    # ==================================================
    # Pricing
    # ==================================================

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    compare_at_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # ==================================================
    # Inventory
    # ==================================================

    stock_quantity = models.PositiveIntegerField(
        default=0,
    )

    track_inventory = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Physical Information
    # ==================================================

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Weight in kilograms.",
    )

    # ==================================================
    # Status
    # ==================================================

    is_active = models.BooleanField(
        default=True,
    )

    is_default = models.BooleanField(
        default=False,
    )

    is_available = models.BooleanField(
        default=True,
        db_index=True,
    )

    # ==================================================
    # Ordering
    # ==================================================

    sort_order = models.PositiveIntegerField(
        default=0,
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

    productvariantimage = models.ForeignKey(
        "vendors.ProductVariantImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "sort_order",
            "created_at",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "product",
                    "name",
                ],
                name=(
                    "unique_variant_name_per_product"
                ),
            ),

            models.UniqueConstraint(
                fields=[
                    "product",
                    "sku",
                ],
                condition=~models.Q(
                    sku="",
                ),
                name=(
                    "unique_variant_sku_per_product"
                ),
            ),

            models.UniqueConstraint(
                fields=[
                    "product",
                ],
                condition=models.Q(
                    is_default=True,
                ),
                name=(
                    "unique_default_variant_per_product"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "product",
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "product",
                    "sort_order",
                ],
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        if self.option_summary:

            return (
                f"{self.product.name} - "
                f"{self.option_summary}"
            )

        return (
            f"{self.product.name} - "
            f"{self.name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate variant configuration.
        """

        # ----------------------------------------------
        # Product
        # ----------------------------------------------

        if self.product_id is None:

            raise ValidationError(
                {
                    "product": (
                        "A product variant must "
                        "belong to a product."
                    )
                }
            )

        # ----------------------------------------------
        # Name
        # ----------------------------------------------

        if not self.name.strip():

            raise ValidationError(
                {
                    "name": (
                        "Variant name cannot "
                        "be empty."
                    )
                }
            )

        # ----------------------------------------------
        # Price
        # ----------------------------------------------

        if (
            self.price is not None
            and self.price < Decimal("0.00")
        ):

            raise ValidationError(
                {
                    "price": (
                        "Variant price cannot "
                        "be negative."
                    )
                }
            )

        # ----------------------------------------------
        # Compare-at price
        # ----------------------------------------------

        if (
            self.compare_at_price is not None
            and self.price is not None
            and self.compare_at_price < self.price
        ):

            raise ValidationError(
                {
                    "compare_at_price": (
                        "Compare-at price cannot "
                        "be lower than the variant "
                        "price."
                    )
                }
            )

        # ----------------------------------------------
        # Weight
        # ----------------------------------------------

        if (
            self.weight is not None
            and self.weight < Decimal("0.000")
        ):

            raise ValidationError(
                {
                    "weight": (
                        "Weight cannot be negative."
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
    # Effective Price
    # ==================================================

    @property
    def effective_price(self):
        """
        Return the price used for checkout.

        Variant price overrides Product price.
        """

        if self.price is not None:

            return self.price

        return self.product.price

    # ==================================================
    # Effective Compare Price
    # ==================================================

    @property
    def effective_compare_at_price(self):
        """
        Return the effective comparison price.
        """

        if self.compare_at_price is not None:

            return self.compare_at_price

        return self.product.compare_at_price

    # ==================================================
    # Inventory
    # ==================================================

    @property
    def is_in_stock(self):
        """
        Determine whether this variant is in stock.
        """

        if not self.track_inventory:

            return True

        return self.stock_quantity > 0

    # ==================================================
    # Availability
    # ==================================================

    @property
    def is_available(self):
        """
        Determine whether this variant can currently
        be purchased.
        """

        if not self.is_active:

            return False

        if not self.product.is_available:

            return False

        if not self.is_in_stock:

            return False

        # Every selected option value must still be
        # active and belong to an active option.
        for value in self.option_values.select_related(
            "option",
        ).all():

            if not value.is_active:

                return False

            if not value.option.is_active:

                return False

        return True

    # ==================================================
    # Option Values
    # ==================================================

    @property
    def selected_option_values(self):
        """
        Return all option values selected by this
        variant.

        This returns the actual variant configuration,
        regardless of whether a value is currently active.
        """

        return self.option_values.select_related(
            "option",
        ).order_by(
            "option__sort_order",
            "sort_order",
            "name",
        )

    # ==================================================
    # Active Option Values
    # ==================================================

    @property
    def active_option_values(self):
        """
        Return currently active selected option values.
        """

        return self.option_values.filter(
            is_active=True,
            option__is_active=True,
        ).select_related(
            "option",
        ).order_by(
            "option__sort_order",
            "sort_order",
            "name",
        )

    # ==================================================
    # Option Value Count
    # ==================================================

    @property
    def option_value_count(self):
        """
        Return the number of option values assigned
        to this variant.
        """

        return self.option_values.count()

    # ==================================================
    # Option Count
    # ==================================================

    @property
    def option_count(self):
        """
        Return the number of distinct product options
        represented by this variant.
        """

        return self.option_values.values(
            "option_id",
        ).distinct().count()

    # ==================================================
    # Has Options
    # ==================================================

    @property
    def has_options(self):
        """
        Determine whether this variant has option
        values.
        """

        return self.option_values.exists()

    # ==================================================
    # Has Complete Options
    # ==================================================

    def has_complete_options(self):
        """
        Determine whether this variant contains exactly
        one value for every active option on the product.

        Useful for validating generated variants.
        """

        active_options = self.product.options.filter(
            is_active=True,
        ).count()

        return (
            self.option_count == active_options
        )

    # ==================================================
    # Option Value Lookup
    # ==================================================

    def has_option_value(
        self,
        option_value,
    ):
        """
        Determine whether this variant contains a
        particular option value.
        """

        if option_value is None:

            return False

        option_value_id = getattr(
            option_value,
            "id",
            option_value,
        )

        return self.option_values.filter(
            pk=option_value_id,
        ).exists()

    # ==================================================
    # Option Lookup
    # ==================================================

    def get_option_value(
        self,
        option,
        default=None,
    ):
        """
        Return the selected value for a particular
        ProductOption.

        Example:

            variant.get_option_value(
                color_option
            )

        Returns:

            Black
        """

        if option is None:

            return default

        option_id = getattr(
            option,
            "id",
            option,
        )

        return (
            self.option_values
            .filter(
                option_id=option_id,
            )
            .first()
            or default
        )

    # ==================================================
    # Variant Description
    # ==================================================

    @property
    def option_summary(self):
        """
        Return a human-readable summary of the variant's
        selected option values.

        Example:

            "Black / Medium"
        """

        values = self.option_values.order_by(
            "option__sort_order",
            "sort_order",
            "name",
        )

        return " / ".join(
            value.name
            for value in values
        )

    # ==================================================
    # Pickup Store
    # ==================================================

    @property
    def pickup_store(self):
        """
        Return the store where this variant is located.
        """

        return self.product.store

    # ==================================================
    # Pickup Location
    # ==================================================

    @property
    def pickup_location(self):
        """
        Return the physical pickup location used by
        dispatch.
        """

        return self.product.pickup_location