from decimal import Decimal
from django.conf import settings
from django.db import models
from django.db.models import Q
import uuid


class Cart(models.Model):
    """
    Shopping cart belonging to a customer.

    A customer can have multiple historical carts,
    but only one active cart at a time.

    The active cart is converted into an Order during
    checkout.

    Cart is responsible for the customer's current
    shopping session.

    CartItem is responsible for the individual products
    or variants inside the cart.
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Customer
    # ==================================================

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="carts",
    )

    # ==================================================
    # Status
    # ==================================================

    is_active = models.BooleanField(
        default=True,
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
            "-created_at",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "customer",
                ],
                condition=Q(
                    is_active=True,
                ),
                name=(
                    "unique_active_cart_per_customer"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "customer",
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "is_active",
                    "updated_at",
                ],
            ),

        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        status = (
            "Active"
            if self.is_active
            else "Inactive"
        )

        return (
            f"Cart #{self.pk} - "
            f"{self.customer.email} - "
            f"{status}"
        )

    # ==================================================
    # Items
    # ==================================================

    @property
    def items_count(self):
        """
        Return the number of distinct cart items.

        Example:

            Cart:
                iPhone
                T-Shirt
                Shoes

        Returns:

            3
        """

        return self.items.count()

    # ==================================================
    # Quantity
    # ==================================================

    @property
    def total_items(self):
        """
        Return the total quantity of products
        in the cart.

        Example:

            iPhone × 2
            Shoes × 1

        Returns:

            3
        """

        return sum(
            (
                item.quantity
                for item in self.items.all()
            ),
            0,
        )

    # ==================================================
    # Subtotal
    # ==================================================

    @property
    def subtotal(self):
        """
        Return the total product value before:

            • Delivery fee
            • Service fee
            • Insurance
            • Discounts
            • Taxes
            • Other checkout charges
        """

        return sum(
            (
                item.subtotal
                for item in self.items.all()
            ),
            Decimal("0.00"),
        )

    # ==================================================
    # Empty
    # ==================================================

    @property
    def is_empty(self):
        """
        Determine whether the cart contains
        any items.
        """

        return not self.items.exists()

    # ==================================================
    # Active
    # ==================================================

    @property
    def is_currently_active(self):
        """
        Determine whether this cart is currently
        active and usable.
        """

        return self.is_active

    # ==================================================
    # Customer
    # ==================================================

    @property
    def customer_id_value(self):
        """
        Return the customer primary key.
        """

        return self.customer_id

    # ==================================================
    # Deactivate
    # ==================================================

    def deactivate(self):
        """
        Mark this cart as inactive.

        Typically called when checkout successfully
        creates an Order.
        """

        if not self.is_active:
            return self

        self.is_active = False

        self.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        return self

    # ==================================================
    # Reactivate
    # ==================================================

    def reactivate(self):
        """
        Reactivate this cart.

        This should only be used when there is no other
        active cart for the customer.
        """

        self.is_active = True

        self.save(
            update_fields=[
                "is_active",
                "updated_at",
            ],
        )

        return self
