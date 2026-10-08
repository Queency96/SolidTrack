from decimal import Decimal

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class ProductVariant(models.Model):
    """
    Represents a purchasable variation of a Product.

    Each variant maintains its own SKU, price, stock, weight,
    active status, and availability.

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

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = ["sort_order", "created_at"]

        constraints = [

            models.UniqueConstraint(
                fields=["product", "name"],
                name="unique_variant_name_per_product",
            ),

            models.UniqueConstraint(
                fields=["product", "sku"],
                condition=~models.Q(sku=""),
                name="unique_variant_sku_per_product",
            ),

            models.UniqueConstraint(
                fields=["product"],
                condition=models.Q(is_default=True),
                name="unique_default_variant_per_product",
            ),
        ]

        indexes = [

            models.Index(
                fields=["product", "is_active"],
            ),

            models.Index(
                fields=["product", "sort_order"],
            ),

            models.Index(
                fields=["product", "is_available"],
            ),
        ]

    # ==================================================
    # Option-value link helper
    # ==================================================

    def _option_links(self):
        """
        Return the variant's option-value links.

        Prefers the prefetched list installed by
        PublicProductQuerySetMixin (to_attr
        "_prefetched_variant_option_links") so callers
        avoid N+1 queries. Falls back to a queryset when
        the prefetch is not present.
        """

        prefetched = getattr(
            self,
            "_prefetched_variant_option_links",
            None,
        )

        if prefetched is not None:
            return prefetched

        return (
            self.variant_option_values
            .select_related(
                "option_value",
                "option_value__option",
            )
        )

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        summary = self.option_summary

        if summary:
            return f"{self.product.name} - {summary}"

        return f"{self.product.name} - {self.name}"

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        if self.product_id is None:

            raise ValidationError(
                {
                    "product": (
                        "A product variant must belong "
                        "to a product."
                    )
                }
            )

        if not self.name.strip():

            raise ValidationError(
                {
                    "name": (
                        "Variant name cannot be empty."
                    )
                }
            )

        if (
            self.price is not None
            and self.price < Decimal("0.00")
        ):

            raise ValidationError(
                {
                    "price": (
                        "Variant price cannot be "
                        "negative."
                    )
                }
            )

        if (
            self.compare_at_price is not None
            and self.price is not None
            and self.compare_at_price < self.price
        ):

            raise ValidationError(
                {
                    "compare_at_price": (
                        "Compare-at price cannot be "
                        "lower than the variant price."
                    )
                }
            )

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

    def save(self, *args, **kwargs):

        if self._state.adding or kwargs.pop(
            "full_clean",
            False,
        ):
            self.full_clean()

        super().save(*args, **kwargs)

    # ==================================================
    # Effective Price
    # ==================================================

    @property
    def effective_price(self):

        if self.price is not None:
            return self.price

        return self.product.price

    @property
    def effective_compare_at_price(self):

        if self.compare_at_price is not None and (
            self.price is None
            or self.compare_at_price >= self.price
        ):
            return self.compare_at_price

        return self.product.compare_at_price

    # ==================================================
    # Inventory
    # ==================================================

    @property
    def is_in_stock(self):

        if not self.track_inventory:
            return True

        return self.stock_quantity > 0

    # ==================================================
    # Purchase Availability
    # ==================================================

    @property
    def can_be_purchased(self):
        """
        Determine whether this variant can currently
        be purchased.

        Consumes the prefetched option-value links when
        available to avoid N+1 queries.

        NOTE: ProductOption uses `is_active`.
        """

        if not self.is_active:
            return False

        if not self.is_available:
            return False

        if not self.product.is_available:
            return False

        if not self.is_in_stock:
            return False

        for link in self._option_links():

            value = link.option_value
            option = value.option

            if not value.is_active:
                return False

            if not option.is_active:
                return False

        return True

    # ==================================================
    # Selected Option Values
    # ==================================================

    @property
    def selected_option_values(self):
        """
        Return option-value instances selected on this variant,
        ordered by option sort_order then value sort_order.
        """

        links = list(self._option_links())

        links.sort(
            key=lambda link: (
                link.option_value.option.sort_order,
                link.option_value.sort_order,
                link.option_value.name,
            )
        )

        return [
            link.option_value
            for link in links
        ]

    # ==================================================
    # Active Option Values
    # ==================================================

    @property
    def active_option_values(self):
        """
        Selected option values that are themselves active and
        whose parent option is active.

        NOTE: ProductOption uses `is_active`.
        """

        return [
            value
            for value in self.selected_option_values
            if value.is_active and value.option.is_active
        ]

    # ==================================================
    # Option Value Count
    # ==================================================

    @property
    def option_value_count(self):

        return len(self._option_links())

    # ==================================================
    # Option Count
    # ==================================================

    @property
    def option_count(self):
        """
        Return the number of distinct ProductOption instances
        covered by this variant's option values.
        """

        return len(
            {
                link.option_value.option_id
                for link in self._option_links()
            }
        )

    # ==================================================
    # Has Options
    # ==================================================

    @property
    def has_options(self):

        return bool(self._option_links())

    # ==================================================
    # Has Complete Options
    # ==================================================

    def has_complete_options(self):
        """
        Determine whether this variant covers every active
        option on its parent product.

        NOTE: ProductOption uses `is_active`.
        """

        active_options = (
            self.product.options
            .filter(is_active=True)
            .count()
        )

        return self.option_count == active_options

    # ==================================================
    # Option Value Lookup
    # ==================================================

    def has_option_value(self, option_value):

        if option_value is None:
            return False

        option_value_id = getattr(
            option_value,
            "id",
            option_value,
        )

        return any(
            link.option_value_id == option_value_id
            for link in self._option_links()
        )

    # ==================================================
    # Option Lookup
    # ==================================================

    def get_option_value(self, option, default=None):

        if option is None:
            return default

        option_id = getattr(option, "id", option)

        for link in self._option_links():

            if link.option_value.option_id == option_id:
                return link.option_value

        return default

    # ==================================================
    # Variant Description
    # ==================================================

    @property
    def option_summary(self):

        values = self.selected_option_values

        return " / ".join(
            value.name for value in values
        )

    # ==================================================
    # Pickup Store
    # ==================================================

    @property
    def pickup_store(self):

        return self.product.store

    # ==================================================
    # Pickup Location
    # ==================================================

    @property
    def pickup_location(self):

        return self.product.pickup_location