from decimal import Decimal
from uuid import UUID

from django.db import transaction

from ..models.cart import Cart
from ..models.cart_item import CartItem

from vendors.models import (
    Product,
    ProductVariant,
)


class CartService:
    """
    Business logic for customer shopping carts.

    Responsibilities
    ----------------
    • Get or create an active customer cart
    • Add products to cart
    • Add product variants to cart
    • Update cart quantities
    • Remove cart items
    • Clear carts
    • Validate cart availability
    • Validate inventory
    • Preserve cart price snapshots

    All public identifiers are expected to be UUIDs.
    """

    # ==================================================
    # Get Active Cart
    # ==================================================

    @staticmethod
    def get_active_cart(
        customer,
    ):
        """
        Return the customer's active cart.

        If the customer does not have an active cart,
        create one.
        """

        if customer is None:

            raise ValueError(
                "Customer is required."
            )

        if not customer.is_authenticated:

            raise ValueError(
                "Authenticated customer is required."
            )

        cart = (
            Cart.objects
            .filter(
                customer=customer,
                is_active=True,
            )
            .first()
        )

        if cart is not None:

            return cart

        return Cart.objects.create(
            customer=customer,
            is_active=True,
        )

    # ==================================================
    # Add Item
    # ==================================================

    @classmethod
    @transaction.atomic
    def add_item(
        cls,
        customer,
        product_id,
        quantity=1,
        variant_id=None,
    ):
        """
        Add a product or product variant to the
        customer's active cart.

        If the item already exists, increase its
        quantity.
        """

        if customer is None:

            raise ValueError(
                "Customer is required."
            )

        quantity = cls._validate_quantity(
            quantity,
        )

        cart = cls.get_active_cart(
            customer,
        )

        product = cls._get_product(
            product_id,
        )

        if not product.is_available:

            raise ValueError(
                "Product is not available."
            )

        variant = None

        if variant_id is not None:

            variant = cls._get_variant(
                variant_id,
            )

            cls._validate_variant(
                product=product,
                variant=variant,
            )

        cls._validate_stock(
            product=product,
            variant=variant,
            quantity=quantity,
        )

        cart_item = (
            CartItem.objects
            .select_for_update()
            .filter(
                cart=cart,
                product=product,
                variant=variant,
            )
            .first()
        )

        if cart_item is not None:

            new_quantity = (
                cart_item.quantity
                + quantity
            )

            cls._validate_stock(
                product=product,
                variant=variant,
                quantity=new_quantity,
            )

            cart_item.quantity = (
                new_quantity
            )

            cart_item.save(
                update_fields=[
                    "quantity",
                    "updated_at",
                ],
            )

            return cart_item

        unit_price = cls._get_current_price(
            product=product,
            variant=variant,
        )

        cart_item = CartItem(
            cart=cart,
            product=product,
            variant=variant,
            quantity=quantity,
            unit_price=unit_price,
        )

        cart_item.save()

        return cart_item

    # ==================================================
    # Update Item
    # ==================================================

    @classmethod
    @transaction.atomic
    def update_item(
        cls,
        customer,
        item_id,
        quantity,
    ):
        """
        Update the quantity of an existing cart item.
        """

        quantity = cls._validate_quantity(
            quantity,
        )

        item_id = cls._parse_uuid(
            item_id,
            "cart item ID",
        )

        cart = cls.get_active_cart(
            customer,
        )

        cart_item = (
            CartItem.objects
            .select_for_update()
            .select_related(
                "product",
                "variant",
            )
            .filter(
                pk=item_id,
                cart=cart,
            )
            .first()
        )

        if cart_item is None:

            raise ValueError(
                "Cart item not found."
            )

        cls._validate_item_availability(
            cart_item,
        )

        cls._validate_stock(
            product=cart_item.product,
            variant=cart_item.variant,
            quantity=quantity,
        )

        cart_item.quantity = quantity

        cart_item.save(
            update_fields=[
                "quantity",
                "updated_at",
            ],
        )

        return cart_item

    # ==================================================
    # Increase Quantity
    # ==================================================

    @classmethod
    @transaction.atomic
    def increase_quantity(
        cls,
        customer,
        item_id,
        quantity=1,
    ):
        """
        Increase the quantity of an existing cart item.
        """

        quantity = cls._validate_quantity(
            quantity,
        )

        item_id = cls._parse_uuid(
            item_id,
            "cart item ID",
        )

        cart = cls.get_active_cart(
            customer,
        )

        cart_item = (
            CartItem.objects
            .select_for_update()
            .select_related(
                "product",
                "variant",
            )
            .filter(
                pk=item_id,
                cart=cart,
            )
            .first()
        )

        if cart_item is None:

            raise ValueError(
                "Cart item not found."
            )

        cls._validate_item_availability(
            cart_item,
        )

        new_quantity = (
            cart_item.quantity
            + quantity
        )

        cls._validate_stock(
            product=cart_item.product,
            variant=cart_item.variant,
            quantity=new_quantity,
        )

        cart_item.quantity = new_quantity

        cart_item.save(
            update_fields=[
                "quantity",
                "updated_at",
            ],
        )

        return cart_item

    # ==================================================
    # Decrease Quantity
    # ==================================================

    @classmethod
    @transaction.atomic
    def decrease_quantity(
        cls,
        customer,
        item_id,
        quantity=1,
    ):
        """
        Decrease the quantity of an existing cart item.

        Remove the item when its quantity reaches zero.
        """

        quantity = cls._validate_quantity(
            quantity,
        )

        item_id = cls._parse_uuid(
            item_id,
            "cart item ID",
        )

        cart = cls.get_active_cart(
            customer,
        )

        cart_item = (
            CartItem.objects
            .select_for_update()
            .select_related(
                "product",
                "variant",
            )
            .filter(
                pk=item_id,
                cart=cart,
            )
            .first()
        )

        if cart_item is None:

            raise ValueError(
                "Cart item not found."
            )

        new_quantity = (
            cart_item.quantity
            - quantity
        )

        if new_quantity <= 0:

            cart_item.delete()

            return None

        cls._validate_item_availability(
            cart_item,
        )

        cart_item.quantity = new_quantity

        cart_item.save(
            update_fields=[
                "quantity",
                "updated_at",
            ],
        )

        return cart_item

    # ==================================================
    # Remove Item
    # ==================================================

    @classmethod
    @transaction.atomic
    def remove_item(
        cls,
        customer,
        item_id,
    ):
        """
        Remove an item from the active cart.
        """

        item_id = cls._parse_uuid(
            item_id,
            "cart item ID",
        )

        cart = cls.get_active_cart(
            customer,
        )

        cart_item = (
            CartItem.objects
            .select_for_update()
            .filter(
                pk=item_id,
                cart=cart,
            )
            .first()
        )

        if cart_item is None:

            raise ValueError(
                "Cart item not found."
            )

        cart_item.delete()

        return True

    # ==================================================
    # Clear Cart
    # ==================================================

    @classmethod
    @transaction.atomic
    def clear_cart(
        cls,
        customer,
    ):
        """
        Remove all items from the active cart.
        """

        cart = cls.get_active_cart(
            customer,
        )

        deleted_count, _ = (
            cart.items.all().delete()
        )

        return deleted_count

    # ==================================================
    # Deactivate Cart
    # ==================================================

    @classmethod
    @transaction.atomic
    def deactivate_cart(
        cls,
        customer,
    ):
        """
        Deactivate the active cart.

        Normally called as part of a successful
        checkout transaction.
        """

        cart = cls.get_active_cart(
            customer,
        )

        cart.deactivate()

        return cart

    # ==================================================
    # Cart Summary
    # ==================================================

    @classmethod
    def get_summary(
        cls,
        customer,
    ):
        """
        Return a lightweight cart summary.
        """

        cart = cls.get_active_cart(
            customer,
        )

        return {
            "cart_id": cart.pk,
            "items_count": cart.items_count,
            "total_items": cart.total_items,
            "subtotal": cart.subtotal,
            "is_empty": cart.is_empty,
        }

    # ==================================================
    # Validate Cart
    # ==================================================

    @classmethod
    def validate_cart(
        cls,
        customer,
    ):
        """
        Validate every item in the active cart.

        Returns an empty list when valid.
        """

        cart = cls.get_active_cart(
            customer,
        )

        errors = []

        items = (
            cart.items
            .select_related(
                "product",
                "variant",
            )
        )

        for item in items:

            try:

                cls._validate_item_availability(
                    item,
                )

                cls._validate_stock(
                    product=item.product,
                    variant=item.variant,
                    quantity=item.quantity,
                )

            except ValueError as exc:

                errors.append(
                    {
                        "item_id": item.pk,
                        "product_id": item.product_id,
                        "variant_id": item.variant_id,
                        "error": str(exc),
                    }
                )

        return errors

    # ==================================================
    # Require Valid Cart
    # ==================================================

    @classmethod
    def require_valid_cart(
        cls,
        customer,
    ):
        """
        Return a valid active cart.

        Raise ValueError when the cart cannot proceed
        to checkout.
        """

        cart = cls.get_active_cart(
            customer,
        )

        if cart.is_empty:

            raise ValueError(
                "Cart is empty."
            )

        errors = cls.validate_cart(
            customer,
        )

        if errors:

            raise ValueError(
                {
                    "cart_errors": errors,
                }
            )

        return cart

    # ==================================================
    # Get Item
    # ==================================================

    @classmethod
    def get_item(
        cls,
        customer,
        item_id,
    ):
        """
        Return one cart item belonging to the
        customer's active cart.
        """

        item_id = cls._parse_uuid(
            item_id,
            "cart item ID",
        )

        cart = cls.get_active_cart(
            customer,
        )

        item = (
            cart.items
            .select_related(
                "product",
                "variant",
            )
            .filter(
                pk=item_id,
            )
            .first()
        )

        if item is None:

            raise ValueError(
                "Cart item not found."
            )

        return item

    # ==================================================
    # Product Resolver
    # ==================================================

    @staticmethod
    def _get_product(
        product_id,
    ):
        """
        Retrieve a product using its UUID.
        """

        product_id = CartService._parse_uuid(
            product_id,
            "product ID",
        )

        product = (
            Product.objects
            .select_related(
                "store",
                "vendor",
            )
            .filter(
                pk=product_id,
            )
            .first()
        )

        if product is None:

            raise ValueError(
                "Product not found."
            )

        return product

    # ==================================================
    # Variant Resolver
    # ==================================================

    @staticmethod
    def _get_variant(
        variant_id,
    ):
        """
        Retrieve a product variant using its UUID.
        """

        variant_id = CartService._parse_uuid(
            variant_id,
            "variant ID",
        )

        variant = (
            ProductVariant.objects
            .select_related(
                "product",
            )
            .filter(
                pk=variant_id,
            )
            .first()
        )

        if variant is None:

            raise ValueError(
                "Product variant not found."
            )

        return variant

    # ==================================================
    # Variant Validation
    # ==================================================

    @staticmethod
    def _validate_variant(
        product,
        variant,
    ):
        """
        Ensure that the selected variant belongs
        to the selected product.
        """

        if variant.product_id != product.pk:

            raise ValueError(
                "Selected variant does not "
                "belong to this product."
            )

        if not variant.is_available:

            raise ValueError(
                "Selected product variant "
                "is not available."
            )

    # ==================================================
    # Stock Validation
    # ==================================================

    @staticmethod
    def _validate_stock(
        product,
        variant,
        quantity,
    ):
        """
        Validate available inventory.
        """

        if variant is not None:

            if not variant.track_inventory:

                return

            if (
                quantity
                > variant.stock_quantity
            ):

                raise ValueError(
                    "Insufficient stock for "
                    "the selected variant."
                )

            return

        if not product.track_inventory:

            return

        if (
            quantity
            > product.stock_quantity
        ):

            raise ValueError(
                "Insufficient product stock."
            )

    # ==================================================
    # Availability Validation
    # ==================================================

    @staticmethod
    def _validate_item_availability(
        item,
    ):
        """
        Validate that a cart item can still be
        purchased.
        """

        if item.variant is not None:

            if not item.variant.is_available:

                raise ValueError(
                    "Selected product variant "
                    "is no longer available."
                )

            return

        if not item.product.is_available:

            raise ValueError(
                "Product is no longer available."
            )

    # ==================================================
    # Price
    # ==================================================

    @staticmethod
    def _get_current_price(
        product,
        variant,
    ):
        """
        Return the current price for a new cart item.
        """

        if variant is not None:

            price = variant.effective_price

        else:

            price = product.price

        if price is None:

            raise ValueError(
                "Product does not have a valid price."
            )

        price = Decimal(
            str(price),
        )

        if price < Decimal("0.00"):

            raise ValueError(
                "Product price cannot be negative."
            )

        return price

    # ==================================================
    # UUID Parser
    # ==================================================

    @staticmethod
    def _parse_uuid(
        value,
        field_name,
    ):
        """
        Convert a value to UUID.

        Accepts both:

            UUID object

        and:

            UUID string
        """

        try:

            return UUID(
                str(value),
            )

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):

            raise ValueError(
                f"Invalid {field_name}."
            )

    # ==================================================
    # Quantity Validation
    # ==================================================

    @staticmethod
    def _validate_quantity(
        quantity,
    ):
        """
        Normalize and validate quantity.
        """

        try:

            quantity = int(
                quantity,
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                "Quantity must be a valid integer."
            )

        if quantity <= 0:

            raise ValueError(
                "Quantity must be greater than zero."
            )

        return quantity