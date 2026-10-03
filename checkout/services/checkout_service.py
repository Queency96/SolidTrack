from collections import defaultdict
from decimal import Decimal
import uuid

from django.db import transaction
from django.utils import timezone

from order.models import (
    Order,
    OrderItem,
    OrderAddress,
    OrderPayment,
    OrderFulfillment,
)
from vendors.models import (
    Product,
    ProductVariant,
)
from deliveries.services.pricing_service import PricingService


class CheckoutService:
    """
    Coordinates the complete checkout process.

    Canonical order-creation entry point (O2-A).

    See module docstring in original.
    """

    # ==================================================
    # Create Order
    # ==================================================

    @classmethod
    @transaction.atomic
    def create_order(
        cls,
        *,
        customer,
        cart,
        shipping_address,
        billing_address=None,
        payment_method=None,
        customer_note="",
        package_size="SMALL",
        delivery_type="INSTANT",
        vehicle_type=None,
        scheduled_at=None,
        insurance=False,
        declared_value=Decimal("0.00"),
        coupon=None,
    ):
        cls._validate_customer(customer=customer)

        cart = cls._lock_cart(cart=cart, customer=customer)

        cart_items = cls._get_cart_items(cart=cart)
        if not cart_items:
            raise ValueError("Cannot checkout an empty cart.")

        locked_items = cls._lock_inventory(cart_items=cart_items)

        subtotal = cls._calculate_subtotal(cart_items=locked_items)

        delivery_address = cls._normalize_address(
            address=shipping_address,
            customer=customer,
        )

        pricing = cls._calculate_order_pricing(
            cart_items=locked_items,
            shipping_address=delivery_address,
            customer=customer,
            package_size=package_size,
            vehicle_type=vehicle_type,
            insurance=insurance,
            declared_value=declared_value,
            coupon=coupon,
        )

        delivery_fee = pricing["delivery_fee"]
        service_fee = pricing["service_fee"]
        insurance_fee = pricing["insurance_fee"]
        discount_amount = pricing["discount_amount"]
        tax_amount = pricing["tax_amount"]

        total_amount = cls._calculate_total(
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            service_fee=service_fee,
            insurance_fee=insurance_fee,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
        )

        order_number = cls._generate_order_number()

        order = Order.objects.create(
            customer=customer,
            order_number=order_number,
            status=Order.Status.PENDING,
            payment_status=Order.PaymentStatus.PENDING,
            payment_method=(payment_method or ""),
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            service_fee=service_fee,
            insurance_fee=insurance_fee,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency="NGN",
            customer_note=(customer_note or ""),
        )

        order_items = cls._create_order_items(
            order=order,
            cart_items=locked_items,
        )

        fulfillments = cls._create_fulfillments(
            order=order,
            order_items=order_items,
            shipping_address=shipping_address,
            pricing_by_store=pricing["by_store"],
            package_size=package_size,
            delivery_type=delivery_type,
            vehicle_type=vehicle_type,
            scheduled_at=scheduled_at,
        )

        cls._create_order_address(
            order=order,
            customer=customer,
            address=shipping_address,
            address_type=OrderAddress.AddressType.SHIPPING,
        )

        if billing_address is not None:
            cls._create_order_address(
                order=order,
                customer=customer,
                address=billing_address,
                address_type=OrderAddress.AddressType.BILLING,
            )

        payment = cls._create_payment(
            order=order,
            customer=customer,
            payment_method=payment_method,
            amount=total_amount,
        )

        cls._deactivate_cart(cart=cart)

        return {
            "order": order,
            "payment": payment,
            "order_items": order_items,
            "fulfillments": fulfillments,
            "pricing": pricing,
        }

    # ==================================================
    # Pricing
    # ==================================================

    @classmethod
    def _calculate_order_pricing(
        cls,
        *,
        cart_items,
        shipping_address,
        customer,
        package_size,
        vehicle_type,
        insurance,
        declared_value,
        coupon,
    ):
        """
        Calculate delivery pricing independently for each store.

        NOTE
        ----
        PricingService._get_route requires these key names:

            pickup_latitude
            pickup_longitude
            destination_latitude
            destination_longitude

        The previous implementation used `*_lat` / `*_lng`,
        which raised "Missing route coordinates" on every call.
        """

        items_by_store = defaultdict(list)

        for item in cart_items:
            store = item.product.store
            if store is None:
                raise ValueError(
                    f"{item.product.name} does not have a pickup store."
                )
            items_by_store[store.id].append(item)

        total_delivery_fee = Decimal("0.00")
        total_service_fee = Decimal("0.00")
        total_insurance_fee = Decimal("0.00")
        total_discount = Decimal("0.00")

        pricing_by_store = {}

        for store_id, items in items_by_store.items():

            store = items[0].product.store

            pickup_latitude = store.latitude
            pickup_longitude = store.longitude
            destination_latitude = shipping_address["latitude"]
            destination_longitude = shipping_address["longitude"]

            if pickup_latitude is None or pickup_longitude is None:
                raise ValueError(
                    f"Store {store.name} does not have valid pickup coordinates."
                )

            if destination_latitude is None or destination_longitude is None:
                raise ValueError(
                    "Shipping address must contain latitude and longitude "
                    "for delivery pricing."
                )

            package_quantity = sum(item.quantity for item in items)

            pricing_data = {
                "pickup_latitude": pickup_latitude,
                "pickup_longitude": pickup_longitude,
                "destination_latitude": destination_latitude,
                "destination_longitude": destination_longitude,
                "package_size": package_size,
                "vehicle_type": vehicle_type,
                "insurance": insurance,
                "declared_value": declared_value,
                "package_quantity": package_quantity,
            }

            result = PricingService.estimate(
                data=pricing_data,
                customer=customer,
                coupon=coupon,
            )

            delivery_base = Decimal(str(result.get("subtotal", "0.00")))
            surge_fee = Decimal(str(result.get("surge_fee", "0.00")))
            service_fee = Decimal(str(result.get("service_fee", "0.00")))
            insurance_fee = Decimal(str(result.get("insurance_fee", "0.00")))
            discount = Decimal(str(result.get("discount", "0.00")))

            delivery_fee = (delivery_base + surge_fee).quantize(Decimal("0.01"))

            store_pricing = {
                "store": store,
                "distance": Decimal(str(result.get("distance", "0.00"))),
                "distance_price": Decimal(str(result.get("distance_price", "0.00"))),
                "package_fee": Decimal(str(result.get("package_fee", "0.00"))),
                "vehicle_multiplier": Decimal(str(result.get("vehicle_multiplier", "1.00"))),
                "delivery_fee": delivery_fee,
                "surge_fee": surge_fee,
                "service_fee": service_fee,
                "insurance_fee": insurance_fee,
                "discount_amount": discount,
                "total": (
                    delivery_fee + service_fee + insurance_fee - discount
                ).quantize(Decimal("0.01")),
            }

            pricing_by_store[store_id] = store_pricing

            total_delivery_fee += delivery_fee
            total_service_fee += service_fee
            total_insurance_fee += insurance_fee
            total_discount += discount

        tax_amount = cls._calculate_tax(
            subtotal=cls._calculate_subtotal(cart_items=cart_items),
            delivery_fee=total_delivery_fee,
            service_fee=total_service_fee,
            insurance_fee=total_insurance_fee,
            discount_amount=total_discount,
        )

        return {
            "delivery_fee": total_delivery_fee.quantize(Decimal("0.01")),
            "service_fee": total_service_fee.quantize(Decimal("0.01")),
            "insurance_fee": total_insurance_fee.quantize(Decimal("0.01")),
            "discount_amount": total_discount.quantize(Decimal("0.01")),
            "tax_amount": tax_amount.quantize(Decimal("0.01")),
            "by_store": pricing_by_store,
        }

    # ==================================================
    # Customer Validation
    # ==================================================

    @staticmethod
    def _validate_customer(*, customer):
        if customer is None:
            raise ValueError("A customer is required.")
        if not customer.is_authenticated:
            raise ValueError("Customer must be authenticated.")

    # ==================================================
    # Cart Locking
    # ==================================================

    @staticmethod
    def _lock_cart(*, cart, customer):
        if cart is None:
            raise ValueError("Cart is required.")

        locked_cart = (
            cart.__class__.objects
            .select_for_update()
            .filter(pk=cart.pk)
            .first()
        )

        if locked_cart is None:
            raise ValueError("Cart was not found.")

        if locked_cart.customer_id != customer.id:
            raise ValueError("This cart does not belong to the customer.")

        if not locked_cart.is_active:
            raise ValueError("This cart is no longer active.")

        return locked_cart

    # ==================================================
    # Cart Items
    # ==================================================

    @staticmethod
    def _get_cart_items(*, cart):
        return list(
            cart.items
            .select_related(
                "product",
                "product__store",
                "variant",
                "variant__product",
            )
            .all()
        )

    # ==================================================
    # Inventory
    # ==================================================

    @classmethod
    def _lock_inventory(cls, *, cart_items):
        locked_items = []

        for cart_item in cart_items:

            quantity = cart_item.quantity
            if quantity <= 0:
                raise ValueError("Cart contains an invalid quantity.")

            if cart_item.variant_id is not None:

                try:
                    variant = (
                        ProductVariant.objects
                        .select_for_update()
                        .select_related("product")
                        .get(pk=cart_item.variant_id)
                    )
                except ProductVariant.DoesNotExist:
                    raise ValueError("The selected product variant no longer exists.")

                try:
                    product = (
                        Product.objects
                        .select_for_update()
                        .select_related("store")
                        .get(pk=cart_item.product_id)
                    )
                except Product.DoesNotExist:
                    raise ValueError("The selected product no longer exists.")

                if variant.product_id != product.id:
                    raise ValueError(
                        "The selected variant does not belong to the product."
                    )
                if not product.is_available:
                    raise ValueError(f"{product.name} is no longer available.")
                if not variant.is_available:
                    raise ValueError(
                        f"The selected variant for {product.name} is no longer available."
                    )
                if not variant.can_be_purchased:
                    raise ValueError(
                        f"The selected variant for {product.name} is no longer available."
                    )

                if variant.track_inventory:
                    if quantity > variant.stock_quantity:
                        raise ValueError(f"Insufficient stock for {product.name}.")
                    variant.stock_quantity -= quantity
                    variant.save(update_fields=["stock_quantity", "updated_at"])

                cart_item.product = product
                cart_item.variant = variant

            else:

                try:
                    product = (
                        Product.objects
                        .select_for_update()
                        .select_related("store")
                        .get(pk=cart_item.product_id)
                    )
                except Product.DoesNotExist:
                    raise ValueError("The selected product no longer exists.")

                if not product.is_available:
                    raise ValueError(f"{product.name} is no longer available.")

                if product.track_inventory:
                    if quantity > product.stock_quantity:
                        raise ValueError(f"Insufficient stock for {product.name}.")
                    product.stock_quantity -= quantity
                    product.save(update_fields=["stock_quantity", "updated_at"])

                cart_item.product = product

            store = product.store
            if store is None:
                raise ValueError(f"{product.name} does not have a pickup store.")
            if not store.can_accept_pickup:
                raise ValueError(
                    f"{store.name} is currently unable to accept pickups."
                )
            if product.vendor_id != store.vendor_id:
                raise ValueError(
                    f"The pickup store for {product.name} does not belong to its vendor."
                )

            locked_items.append(cart_item)

        return locked_items

    # ==================================================
    # Product Subtotal
    # ==================================================

    @staticmethod
    def _calculate_subtotal(*, cart_items):
        subtotal = Decimal("0.00")
        for item in cart_items:
            subtotal += item.unit_price * Decimal(str(item.quantity))
        return subtotal.quantize(Decimal("0.01"))

    # ==================================================
    # Tax
    # ==================================================

    @staticmethod
    def _calculate_tax(
        *, subtotal, delivery_fee, service_fee, insurance_fee, discount_amount,
    ):
        return Decimal("0.00")

    # ==================================================
    # Total
    # ==================================================

    @staticmethod
    def _calculate_total(
        *, subtotal, delivery_fee, service_fee, insurance_fee,
        discount_amount, tax_amount,
    ):
        total = (
            subtotal + delivery_fee + service_fee
            + insurance_fee + tax_amount - discount_amount
        )
        if total < Decimal("0.00"):
            total = Decimal("0.00")
        return total.quantize(Decimal("0.01"))

    # ==================================================
    # Order Number
    # ==================================================

    @staticmethod
    def _generate_order_number():
        return (
            f"ORD-{timezone.now():%Y%m%d}-"
            f"{uuid.uuid4().hex[:10].upper()}"
        )

    # ==================================================
    # Order Items
    # ==================================================

    @classmethod
    def _create_order_items(cls, *, order, cart_items):
        order_items = []

        for cart_item in cart_items:

            product = cart_item.product
            variant = cart_item.variant
            store = product.store

            quantity = cart_item.quantity
            unit_price = cart_item.unit_price

            subtotal = (unit_price * Decimal(str(quantity))).quantize(
                Decimal("0.01")
            )

            order_item = OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                store=store,
                product_name=product.name,
                product_sku=(product.sku or ""),
                variant_name=(variant.name if variant is not None else ""),
                variant_sku=(variant.sku if variant is not None else ""),
                option_summary=(variant.option_summary if variant is not None else ""),
                store_name=store.name,
                store_address_line_1=store.address_line_1,
                store_address_line_2=(store.address_line_2 or ""),
                store_city=store.city,
                store_state=store.state,
                store_country=(store.country or "Nigeria"),
                store_postal_code=(store.postal_code or ""),
                store_latitude=store.latitude,
                store_longitude=store.longitude,
                unit_price=unit_price,
                quantity=quantity,
                subtotal=subtotal,
                currency="NGN",
            )

            order_items.append(order_item)

        return order_items

    # ==================================================
    # Fulfillments
    # ==================================================

    @classmethod
    def _create_fulfillments(
        cls,
        *,
        order,
        order_items,
        shipping_address,
        pricing_by_store,
        package_size,
        delivery_type,
        vehicle_type,
        scheduled_at,
    ):
        items_by_store = defaultdict(list)
        for order_item in order_items:
            if order_item.store_id is None:
                raise ValueError("Order item must have a store.")
            items_by_store[order_item.store_id].append(order_item)

        delivery = cls._normalize_address(
            address=shipping_address,
            customer=order.customer,
        )

        fulfillments = []

        for store_id, items in items_by_store.items():

            store = items[0].store
            if store is None:
                raise ValueError("Order item store could not be resolved.")

            vendor = store.vendor
            if vendor is None:
                raise ValueError(
                    f"Store {store.name} does not have an associated vendor."
                )

            subtotal = sum(
                (item.subtotal for item in items),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))

            pricing = pricing_by_store.get(store_id)
            if pricing is None:
                raise ValueError(
                    f"Pricing was not calculated for store {store.name}."
                )

            delivery_fee = pricing["delivery_fee"]
            service_fee = pricing["service_fee"]
            insurance_fee = pricing["insurance_fee"]
            discount_amount = pricing["discount_amount"]
            tax_amount = Decimal("0.00")

            total_amount = (
                subtotal + delivery_fee + service_fee
                + insurance_fee + tax_amount - discount_amount
            )
            if total_amount < Decimal("0.00"):
                total_amount = Decimal("0.00")
            total_amount = total_amount.quantize(Decimal("0.01"))

            fulfillment = OrderFulfillment.objects.create(
                order=order,
                store=store,
                vendor=vendor,
                store_name=store.name,
                store_address_line_1=store.address_line_1,
                store_address_line_2=(store.address_line_2 or ""),
                store_city=store.city,
                store_state=store.state,
                store_country=(store.country or "Nigeria"),
                store_postal_code=(store.postal_code or ""),
                store_latitude=store.latitude,
                store_longitude=store.longitude,
                store_pickup_instructions=(
                    getattr(store, "pickup_instructions", "") or ""
                ),
                store_preparation_time_minutes=(
                    getattr(store, "preparation_time_minutes", 0) or 0
                ),
                delivery_address_line_1=delivery["address_line_1"],
                delivery_address_line_2=delivery["address_line_2"],
                delivery_city=delivery["city"],
                delivery_state=delivery["state"],
                delivery_country=delivery["country"],
                delivery_postal_code=delivery["postal_code"],
                delivery_latitude=delivery["latitude"],
                delivery_longitude=delivery["longitude"],
                delivery_instructions=delivery["landmark"],
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                service_fee=service_fee,
                insurance_fee=insurance_fee,
                discount_amount=discount_amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                # O1-A + O3-B: delivery inputs
                package_size=package_size,
                delivery_type=delivery_type,
                vehicle_type=vehicle_type,
                scheduled_at=scheduled_at,
            )

            OrderItem.objects.filter(
                id__in=[item.id for item in items]
            ).update(fulfillment=fulfillment)

            for item in items:
                item.fulfillment = fulfillment

            fulfillments.append(fulfillment)

        return fulfillments

    # ==================================================
    # Address Normalization
    # ==================================================

    @staticmethod
    def _normalize_address(*, address, customer):
        if address is None:
            raise ValueError("Address is required.")

        if isinstance(address, dict):
            address_line_1 = address.get("address_line_1", "")
            address_line_2 = address.get("address_line_2", "") or ""
            city = address.get("city", "")
            state = address.get("state", "")
            country = address.get("country", "Nigeria") or "Nigeria"
            postal_code = address.get("postal_code", "") or ""
            landmark = address.get("landmark", "") or ""
            latitude = address.get("latitude")
            longitude = address.get("longitude")
        else:
            address_line_1 = getattr(address, "address_line_1", "")
            address_line_2 = getattr(address, "address_line_2", "") or ""
            city = getattr(address, "city", "")
            state = getattr(address, "state", "")
            country = getattr(address, "country", "Nigeria") or "Nigeria"
            postal_code = getattr(address, "postal_code", "") or ""
            landmark = getattr(address, "landmark", "") or ""
            latitude = getattr(address, "latitude", None)
            longitude = getattr(address, "longitude", None)

        if not address_line_1:
            raise ValueError("Address line 1 is required.")
        if not city:
            raise ValueError("City is required.")
        if not state:
            raise ValueError("State is required.")
        if latitude is None:
            raise ValueError("Shipping address latitude is required.")
        if longitude is None:
            raise ValueError("Shipping address longitude is required.")

        latitude = Decimal(str(latitude))
        longitude = Decimal(str(longitude))

        if not (Decimal("-90") <= latitude <= Decimal("90")):
            raise ValueError("Latitude must be between -90 and 90.")
        if not (Decimal("-180") <= longitude <= Decimal("180")):
            raise ValueError("Longitude must be between -180 and 180.")

        return {
            "address_line_1": address_line_1,
            "address_line_2": address_line_2,
            "city": city,
            "state": state,
            "country": country,
            "postal_code": postal_code,
            "landmark": landmark,
            "latitude": latitude,
            "longitude": longitude,
        }

    # ==================================================
    # Order Address
    # ==================================================

    @staticmethod
    def _create_order_address(
        *, order, customer, address, address_type,
    ):
        if address is None:
            raise ValueError("Address is required.")

        normalized = CheckoutService._normalize_address(
            address=address,
            customer=customer,
        )

        if isinstance(address, dict):
            recipient_name = (
                address.get("recipient_name", "")
                or customer.get_full_name()
            )
            phone_number = (
                address.get("phone_number", "")
                or getattr(customer, "phone_number", "")
            )
        else:
            recipient_name = (
                getattr(address, "recipient_name", "")
                or customer.get_full_name()
            )
            phone_number = (
                getattr(address, "phone_number", "")
                or getattr(customer, "phone_number", "")
            )

        return OrderAddress.objects.create(
            order=order,
            user=customer,
            address_type=address_type,
            recipient_name=recipient_name,
            phone_number=phone_number,
            address_line_1=normalized["address_line_1"],
            address_line_2=normalized["address_line_2"],
            city=normalized["city"],
            state=normalized["state"],
            country=normalized["country"],
            postal_code=normalized["postal_code"],
            landmark=normalized["landmark"],
            latitude=normalized["latitude"],
            longitude=normalized["longitude"],
        )

    # ==================================================
    # Payment
    # ==================================================

    @staticmethod
    def _create_payment(*, order, customer, payment_method, amount):
        if not payment_method:
            raise ValueError("Payment method is required.")

        method_mapping = {
            Order.PaymentMethod.WALLET: OrderPayment.PaymentMethod.WALLET,
            Order.PaymentMethod.CARD: OrderPayment.PaymentMethod.CARD,
            Order.PaymentMethod.BANK_TRANSFER: OrderPayment.PaymentMethod.BANK_TRANSFER,
            Order.PaymentMethod.CASH: OrderPayment.PaymentMethod.CASH,
        }

        try:
            order_payment_method = method_mapping[payment_method]
        except KeyError:
            raise ValueError("Unsupported payment method.")

        if payment_method == Order.PaymentMethod.WALLET:
            provider = OrderPayment.PaymentProvider.WALLET
        elif payment_method == Order.PaymentMethod.CASH:
            provider = OrderPayment.PaymentProvider.CASH
        else:
            provider = OrderPayment.PaymentProvider.PAYSTACK

        return OrderPayment.objects.create(
            order=order,
            user=customer,
            payment_method=order_payment_method,
            provider=provider,
            status=OrderPayment.PaymentStatus.PENDING,
            amount=amount,
            currency=order.currency,
        )

    # ==================================================
    # Deactivate Cart
    # ==================================================

    @staticmethod
    def _deactivate_cart(*, cart):
        cart.deactivate()