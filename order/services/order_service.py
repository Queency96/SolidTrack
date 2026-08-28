from collections import defaultdict
from decimal import Decimal
import uuid
from django.db import transaction
from cart.services.cart_service import CartService
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.order_fulfillment import OrderFulfillment


class OrderService:
    """
    Business logic for creating and managing customer orders.

    Responsibilities
    ----------------
    • Validate the customer's active cart
    • Create an Order from the cart
    • Create immutable OrderItem snapshots
    • Group order items by VendorStore
    • Create OrderFulfillment records
    • Deactivate the source Cart

    This service does NOT:
        • Process payments
        • Reserve payment funds
        • Dispatch riders
        • Create delivery offers
        • Assign riders
        • Modify historical order prices
    """

    # ==================================================
    # Checkout
    # ==================================================

    @classmethod
    @transaction.atomic
    def checkout(
        cls,
        customer,
        delivery_address,
        customer_note="",
    ):
        """
        Convert the customer's active cart into
        an Order.

        A single Order may contain products from
        multiple VendorStore locations.

        Each unique VendorStore becomes a separate
        OrderFulfillment.

        Parameters
        ----------
        customer:
            Authenticated customer.

        delivery_address:
            Validated delivery destination data.

        customer_note:
            Optional note supplied by the customer.

        Returns
        -------
        Order
            Newly created order.
        """

        # ----------------------------------------------
        # Validate customer
        # ----------------------------------------------

        if customer is None:

            raise ValueError(
                "Customer is required."
            )

        if not customer.is_authenticated:

            raise ValueError(
                "Authenticated customer is required."
            )

        # ----------------------------------------------
        # Validate cart
        # ----------------------------------------------

        cart = CartService.require_valid_cart(
            customer,
        )

        # ----------------------------------------------
        # Lock cart items
        # ----------------------------------------------

        cart_items = list(
            cart.items
            .select_for_update()
            .select_related(
                "product",
                "product__store",
                "product__vendor",
                "variant",
            )
        )

        if not cart_items:

            raise ValueError(
                "Cart is empty."
            )

        # ----------------------------------------------
        # Validate again while transaction is locked
        # ----------------------------------------------

        cls._validate_checkout_items(
            cart_items,
        )

        # ----------------------------------------------
        # Generate order number
        # ----------------------------------------------

        order_number = cls._generate_order_number()

        # ----------------------------------------------
        # Calculate subtotal
        # ----------------------------------------------

        subtotal = cls._calculate_subtotal(
            cart_items,
        )

        # ----------------------------------------------
        # Initial order pricing
        # ----------------------------------------------
        #
        # Delivery/service/insurance/tax/discount
        # calculations can be added once the checkout
        # pricing service is connected.

        delivery_fee = Decimal("0.00")

        service_fee = Decimal("0.00")

        insurance_fee = Decimal("0.00")

        discount_amount = Decimal("0.00")

        tax_amount = Decimal("0.00")

        total_amount = (
            subtotal
            + delivery_fee
            + service_fee
            + insurance_fee
            + tax_amount
            - discount_amount
        )

        if total_amount < Decimal("0.00"):

            total_amount = Decimal(
                "0.00"
            )

        # ----------------------------------------------
        # Create Order
        # ----------------------------------------------

        order = Order.objects.create(
            customer=customer,
            order_number=order_number,
            status=Order.Status.PENDING,
            payment_status=(
                Order.PaymentStatus.PENDING
            ),
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            service_fee=service_fee,
            insurance_fee=insurance_fee,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency="NGN",
            customer_note=customer_note or "",
        )

        # ----------------------------------------------
        # Create OrderItems
        # ----------------------------------------------

        order_items = []

        for cart_item in cart_items:

            order_item = (
                cls._create_order_item(
                    order=order,
                    cart_item=cart_item,
                )
            )

            order_items.append(
                order_item
            )

        # ----------------------------------------------
        # Group items by store
        # ----------------------------------------------

        items_by_store = (
            cls._group_items_by_store(
                order_items,
            )
        )

        # ----------------------------------------------
        # Create fulfillment groups
        # ----------------------------------------------

        fulfillments = []

        for store_id, items in (
            items_by_store.items()
        ):

            fulfillment = (
                cls._create_fulfillment(
                    order=order,
                    store=items[0].store,
                    items=items,
                    delivery_address=(
                        delivery_address
                    ),
                )
            )

            fulfillments.append(
                fulfillment
            )

        # ----------------------------------------------
        # Deactivate cart
        # ----------------------------------------------

        cart.deactivate()

        return order

    # ==================================================
    # Validate Checkout Items
    # ==================================================

    @staticmethod
    def _validate_checkout_items(
        cart_items,
    ):
        """
        Perform final validation before creating
        the historical order.
        """

        for item in cart_items:

            # ------------------------------------------
            # Product availability
            # ------------------------------------------

            if not item.product.is_available:

                raise ValueError(
                    f"Product '{item.product.name}' "
                    "is no longer available."
                )

            # ------------------------------------------
            # Variant validation
            # ------------------------------------------

            if item.variant is not None:

                if (
                    item.variant.product_id
                    != item.product_id
                ):

                    raise ValueError(
                        "Selected variant does not "
                        "belong to the selected product."
                    )

                if not item.variant.is_available:

                    raise ValueError(
                        f"Variant for '{item.product.name}' "
                        "is no longer available."
                    )

                if (
                    item.variant.track_inventory
                    and item.quantity
                    > item.variant.stock_quantity
                ):

                    raise ValueError(
                        f"Insufficient stock for "
                        f"'{item.display_name}'."
                    )

            # ------------------------------------------
            # Product inventory
            # ------------------------------------------

            elif (
                item.product.track_inventory
                and item.quantity
                > item.product.stock_quantity
            ):

                raise ValueError(
                    f"Insufficient stock for "
                    f"'{item.product.name}'."
                )

            # ------------------------------------------
            # Store pickup
            # ------------------------------------------

            store = item.product.store

            if not store.can_accept_orders:

                raise ValueError(
                    f"Store '{store.name}' "
                    "is not currently accepting orders."
                )

            if not store.can_accept_pickup:

                raise ValueError(
                    f"Store '{store.name}' "
                    "is not currently accepting pickups."
                )

    # ==================================================
    # Calculate Subtotal
    # ==================================================

    @staticmethod
    def _calculate_subtotal(
        cart_items,
    ):
        """
        Calculate the order subtotal from the cart
        price snapshots.

        CartItem.unit_price is used deliberately.

        The order must never recalculate its historical
        price from the current Product or Variant price.
        """

        subtotal = Decimal("0.00")

        for item in cart_items:

            subtotal += (
                item.unit_price
                * Decimal(
                    str(item.quantity),
                )
            )

        return subtotal

    # ==================================================
    # Create Order Item
    # ==================================================

    @staticmethod
    def _create_order_item(
        order,
        cart_item,
    ):
        """
        Create an immutable historical snapshot of
        a CartItem.
        """

        product = cart_item.product

        variant = cart_item.variant

        store = product.store

        variant_name = ""

        variant_sku = ""

        option_summary = ""

        if variant is not None:

            variant_name = (
                variant.name or ""
            )

            variant_sku = (
                variant.sku or ""
            )

            option_summary = (
                variant.option_summary or ""
            )

        unit_price = (
            Decimal(
                str(
                    cart_item.unit_price
                )
            )
        )

        subtotal = (
            unit_price
            * Decimal(
                str(cart_item.quantity),
            )
        )

        return OrderItem.objects.create(
            order=order,

            fulfillment=None,

            product=product,
            variant=variant,
            store=store,

            product_name=(
                product.name
            ),

            product_sku=(
                product.sku or ""
            ),

            variant_name=variant_name,

            variant_sku=variant_sku,

            option_summary=(
                option_summary
            ),

            store_name=(
                store.name
            ),

            store_address_line_1=(
                store.address_line_1
            ),

            store_address_line_2=(
                store.address_line_2 or ""
            ),

            store_city=(
                store.city
            ),

            store_state=(
                store.state
            ),

            store_country=(
                store.country
            ),

            store_postal_code=(
                store.postal_code or ""
            ),

            store_latitude=(
                store.latitude
            ),

            store_longitude=(
                store.longitude
            ),

            unit_price=unit_price,

            quantity=cart_item.quantity,

            subtotal=subtotal,

            currency=(
                order.currency
            ),
        )

    # ==================================================
    # Group Items By Store
    # ==================================================

    @staticmethod
    def _group_items_by_store(
        order_items,
    ):
        """
        Group OrderItems according to their
        VendorStore.

        The store primary key is the grouping key.

        Therefore:

            Store A → one fulfillment

            Store B → another fulfillment

        even when both stores belong to the same vendor.
        """

        items_by_store = defaultdict(list)

        for item in order_items:

            items_by_store[
                item.store_id
            ].append(
                item
            )

        return items_by_store

    # ==================================================
    # Create Fulfillment
    # ==================================================

    @staticmethod
    def _create_fulfillment(
        order,
        store,
        items,
        delivery_address,
    ):
        """
        Create one OrderFulfillment for a single
        VendorStore.

        All OrderItems supplied to this method must
        belong to the same store.
        """

        if not items:

            raise ValueError(
                "Cannot create a fulfillment "
                "without order items."
            )

        # ----------------------------------------------
        # Validate same store
        # ----------------------------------------------

        for item in items:

            if item.store_id != store.id:

                raise ValueError(
                    "All fulfillment items must "
                    "belong to the same store."
                )

        # ----------------------------------------------
        # Fulfillment subtotal
        # ----------------------------------------------

        subtotal = sum(
            (
                item.subtotal
                for item in items
            ),
            Decimal("0.00"),
        )

        # ----------------------------------------------
        # Initial fulfillment fees
        # ----------------------------------------------

        delivery_fee = Decimal("0.00")

        service_fee = Decimal("0.00")

        insurance_fee = Decimal("0.00")

        discount_amount = Decimal("0.00")

        tax_amount = Decimal("0.00")

        total_amount = (
            subtotal
            + delivery_fee
            + service_fee
            + insurance_fee
            + tax_amount
            - discount_amount
        )

        # ----------------------------------------------
        # Create fulfillment
        # ----------------------------------------------

        fulfillment = OrderFulfillment.objects.create(

            order=order,

            store=store,

            vendor=store.vendor,

            store_name=(
                store.name
            ),

            store_address_line_1=(
                store.address_line_1
            ),

            store_address_line_2=(
                store.address_line_2 or ""
            ),

            store_city=(
                store.city
            ),

            store_state=(
                store.state
            ),

            store_country=(
                store.country
            ),

            store_postal_code=(
                store.postal_code or ""
            ),

            store_latitude=(
                store.latitude
            ),

            store_longitude=(
                store.longitude
            ),

            store_pickup_instructions=(
                store.pickup_instructions or ""
            ),

            store_preparation_time_minutes=(
                store.preparation_time_minutes
            ),

            status=(
                OrderFulfillment.Status.PENDING
            ),

            subtotal=subtotal,

            delivery_fee=delivery_fee,

            service_fee=service_fee,

            insurance_fee=insurance_fee,

            discount_amount=discount_amount,

            tax_amount=tax_amount,

            total_amount=total_amount,

            delivery_address_line_1=(
                delivery_address[
                    "address_line_1"
                ]
            ),

            delivery_address_line_2=(
                delivery_address.get(
                    "address_line_2",
                    "",
                )
            ),

            delivery_city=(
                delivery_address["city"]
            ),

            delivery_state=(
                delivery_address["state"]
            ),

            delivery_country=(
                delivery_address.get(
                    "country",
                    "Nigeria",
                )
            ),

            delivery_postal_code=(
                delivery_address.get(
                    "postal_code",
                    "",
                )
            ),

            delivery_latitude=(
                delivery_address[
                    "latitude"
                ]
            ),

            delivery_longitude=(
                delivery_address[
                    "longitude"
                ]
            ),

            delivery_instructions=(
                delivery_address.get(
                    "instructions",
                    "",
                )
            ),
        )

        # ----------------------------------------------
        # Attach items to fulfillment
        # ----------------------------------------------

        OrderItem.objects.filter(
            pk__in=[
                item.pk
                for item in items
            ]
        ).update(
            fulfillment=fulfillment,
        )

        return fulfillment

    # ==================================================
    # Order Number
    # ==================================================

    @staticmethod
    def _generate_order_number():
        """
        Generate a human-readable unique order number.

        UUID remains the actual database primary key.

        Example:

            ORD-20260827-A3F92C
        """

        from django.utils import timezone

        timestamp = timezone.now().strftime(
            "%Y%m%d"
        )

        suffix = uuid.uuid4().hex[:6].upper()

        return (
            f"ORD-{timestamp}-{suffix}"
        )