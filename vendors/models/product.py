from decimal import Decimal
import uuid
from django.core.exceptions import ValidationError
from django.db import models


class Product(models.Model):
    """
    Product offered by a vendor through one of the
    vendor's stores.

    A vendor can sell the same type of product from
    different stores by creating separate Product
    records for each store.

    The store attached to the product is also the
    physical pickup location used by the delivery
    system.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ==================================================
    # Vendor
    # ==================================================

    vendor = models.ForeignKey(
        "vendors.VendorProfile",
        on_delete=models.CASCADE,
        related_name="products",
    )

    # ==================================================
    # Store
    # ==================================================

    store = models.ForeignKey(
        "vendors.VendorStore",
        on_delete=models.PROTECT,
        related_name="products",
    )

    # ==================================================
    # Category
    # ==================================================

    category = models.ForeignKey(
        "vendors.ProductCategory",
        on_delete=models.PROTECT,
        related_name="products",
    )

    # ==================================================
    # Product Identity
    # ==================================================

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
        default="",
    )

    # ==================================================
    # Description
    # ==================================================

    short_description = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )

    description = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Pricing
    # ==================================================

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
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
    # Product Status
    # ==================================================

    is_active = models.BooleanField(
        default=True,
    )

    is_published = models.BooleanField(
        default=False,
    )

    is_featured = models.BooleanField(
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
            "-created_at",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "vendor",
                    "slug",
                ],
                name=(
                    "unique_product_slug_per_vendor"
                ),
            ),

            models.UniqueConstraint(
                fields=[
                    "vendor",
                    "sku",
                ],
                condition=~models.Q(
                    sku="",
                ),
                name=(
                    "unique_product_sku_per_vendor"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "vendor",
                    "store",
                ],
            ),

            models.Index(
                fields=[
                    "store",
                    "is_active",
                    "is_published",
                ],
            ),

            models.Index(
                fields=[
                    "category",
                    "is_active",
                    "is_published",
                ],
            ),

            models.Index(
                fields=[
                    "vendor",
                    "is_published",
                ],
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        return (
            f"{self.name} - "
            f"{self.store.name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate product configuration.
        """

        # ----------------------------------------------
        # Store ownership
        # ----------------------------------------------

        if (
            self.vendor_id
            and self.store_id
        ):

            if self.store.vendor_id != self.vendor_id:

                raise ValidationError(
                    {
                        "store": (
                            "The selected store does "
                            "not belong to this vendor."
                        )
                    }
                )

        # ----------------------------------------------
        # Category ownership
        # ----------------------------------------------

        if (
            self.vendor_id
            and self.category_id
        ):

            category_vendor_id = getattr(
                self.category,
                "vendor_id",
                None,
            )

            # A category with no vendor is treated as
            # a global category.
            if (
                category_vendor_id is not None
                and category_vendor_id
                != self.vendor_id
            ):

                raise ValidationError(
                    {
                        "category": (
                            "The selected category "
                            "does not belong to this "
                            "vendor."
                        )
                    }
                )

        # ----------------------------------------------
        # Price
        # ----------------------------------------------

        if self.price < Decimal("0.00"):

            raise ValidationError(
                {
                    "price": (
                        "Product price cannot "
                        "be negative."
                    )
                }
            )

        # ----------------------------------------------
        # Compare-at price
        # ----------------------------------------------

        if (
            self.compare_at_price is not None
            and self.compare_at_price
            < self.price
        ):

            raise ValidationError(
                {
                    "compare_at_price": (
                        "Compare-at price should "
                        "not be lower than the "
                        "selling price."
                    )
                }
            )

        # ----------------------------------------------
        # Inventory
        # ----------------------------------------------

        if self.stock_quantity < 0:

            raise ValidationError(
                {
                    "stock_quantity": (
                        "Stock quantity cannot "
                        "be negative."
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
    # Store
    # ==================================================

    @property
    def pickup_store(self):
        """
        The physical store where this product is
        collected by the rider.
        """

        return self.store

    # ==================================================
    # Pickup Location
    # ==================================================

    @property
    def pickup_location(self):
        """
        Return the product's pickup coordinates.

        Dispatch can use this without needing to know
        anything about the Product model's internals.
        """

        if self.store is None:
            return None

        return self.store.location

    # ==================================================
    # Inventory
    # ==================================================

    @property
    def is_in_stock(self):
        """
        Determine whether the product is currently
        available for purchase.
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
        Determine whether the product can currently
        be presented as purchasable.
        """

        return (
            self.is_active
            and self.is_published
            and self.store.is_active
            and self.store.is_verified
            and self.store.accepting_orders
            and self.is_in_stock
        )