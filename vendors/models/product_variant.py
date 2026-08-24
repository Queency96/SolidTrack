from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models


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

    A product can have multiple variants.

    Each variant maintains its own:
        • SKU
        • price
        • stock
        • weight
        • active status
    """

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
    # Variant Attributes
    # ==================================================
    #
    # Flexible JSON structure allows different product
    # categories to use different attributes.
    #
    # Examples:
    #
    # {
    #     "color": "Black",
    #     "size": "XL"
    # }
    #
    # {
    #     "storage": "256GB",
    #     "color": "Blue"
    # }
    #
    # {
    #     "weight": "2kg",
    #     "flavor": "Chocolate"
    # }

    attributes = models.JSONField(
        default=dict,
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
    # String
    # ==================================================

    def __str__(self):

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

        # ----------------------------------------------
        # Attributes
        # ----------------------------------------------

        if not isinstance(
            self.attributes,
            dict,
        ):

            raise ValidationError(
                {
                    "attributes": (
                        "Variant attributes "
                        "must be a JSON object."
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

        If the variant does not define its own price,
        fall back to the parent Product price.
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
        Return the effective original/comparison price.
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
        Determine whether this variant is available.
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

        return (
            self.is_active
            and self.product.is_available
            and self.is_in_stock
        )

    # ==================================================
    # Attribute Helper
    # ==================================================

    def get_attribute(
        self,
        key,
        default=None,
    ):
        """
        Safely retrieve a variant attribute.
        """

        return self.attributes.get(
            key,
            default,
        )

    # ==================================================
    # Set Attribute
    # ==================================================

    def set_attribute(
        self,
        key,
        value,
    ):
        """
        Add or update a variant attribute.
        """

        if not isinstance(
            self.attributes,
            dict,
        ):
            self.attributes = {}

        self.attributes[key] = value

        return self

    # ==================================================
    # Pickup Location
    # ==================================================

    @property
    def pickup_store(self):
        """
        Return the store where this variant is located.

        The store belongs to the parent product.
        """

        return self.product.store

    @property
    def pickup_location(self):
        """
        Return the physical pickup location used by
        dispatch.
        """

        return self.product.pickup_location
