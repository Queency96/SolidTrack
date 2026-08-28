from rest_framework import serializers
from order.models import (
    Order,
    OrderItem,
    OrderAddress,
    OrderPayment,
    OrderFulfillment,
)


# ==================================================
# Order Item Serializer
# ==================================================

class OrderItemSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only representation of an item purchased
    as part of an Order.

    OrderItem contains historical snapshots of:

        • product
        • variant
        • store
        • pricing

    These snapshots should not change if the original
    product, variant, or store is later modified.
    """

    # ==================================================
    # Computed Fields
    # ==================================================

    display_name = serializers.CharField(
        read_only=True,
    )

    sku = serializers.CharField(
        read_only=True,
    )

    pickup_location = serializers.ReadOnlyField()

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        model = OrderItem

        fields = [
            # ------------------------------------------
            # Identity
            # ------------------------------------------

            "id",
            "order",
            "fulfillment",

            # ------------------------------------------
            # Original References
            # ------------------------------------------

            "product",
            "variant",
            "store",

            # ------------------------------------------
            # Product Snapshot
            # ------------------------------------------

            "product_name",
            "product_sku",

            # ------------------------------------------
            # Variant Snapshot
            # ------------------------------------------

            "variant_name",
            "variant_sku",
            "option_summary",

            # ------------------------------------------
            # Store Snapshot
            # ------------------------------------------

            "store_name",
            "store_address_line_1",
            "store_address_line_2",
            "store_city",
            "store_state",
            "store_country",
            "store_postal_code",
            "store_latitude",
            "store_longitude",

            # ------------------------------------------
            # Pricing
            # ------------------------------------------

            "unit_price",
            "quantity",
            "subtotal",
            "currency",

            # ------------------------------------------
            # Computed
            # ------------------------------------------

            "display_name",
            "sku",
            "pickup_location",

            # ------------------------------------------
            # Timestamp
            # ------------------------------------------

            "created_at",
        ]

        read_only_fields = fields


# ==================================================
# Order Address Serializer
# ==================================================

class OrderAddressSerializer(
    serializers.ModelSerializer,
):
    """
    Immutable address snapshot belonging to an Order.

    This is intentionally different from the customer's
    current Address model.

    OrderAddress represents the exact address used when
    the order was placed.
    """

    # ==================================================
    # Location
    # ==================================================

    location = serializers.SerializerMethodField()

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        model = OrderAddress

        fields = [
            # ------------------------------------------
            # Identity
            # ------------------------------------------

            "id",
            "order",
            "user",
            "address_type",

            # ------------------------------------------
            # Recipient
            # ------------------------------------------

            "recipient_name",
            "phone_number",

            # ------------------------------------------
            # Address
            # ------------------------------------------

            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "country",
            "postal_code",
            "landmark",

            # ------------------------------------------
            # Coordinates
            # ------------------------------------------

            "latitude",
            "longitude",
            "location",

            # ------------------------------------------
            # Timestamp
            # ------------------------------------------

            "created_at",
        ]

        read_only_fields = fields

    # ==================================================
    # Location
    # ==================================================

    def get_location(
        self,
        obj,
    ):
        if (
            obj.latitude is None
            or obj.longitude is None
        ):
            return None

        return {
            "latitude": obj.latitude,
            "longitude": obj.longitude,
        }


# ==================================================
# Order Payment Serializer
# ==================================================

class OrderPaymentSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only representation of an order payment.

    Payment state is controlled by the payment service
    and payment provider.

    The customer must never be able to modify:

        • status
        • provider
        • provider_reference
        • gateway_response
        • paid_at
        • refunded_at
    """

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        model = OrderPayment

        fields = [
            # ------------------------------------------
            # Identity
            # ------------------------------------------

            "id",
            "order",
            "user",

            # ------------------------------------------
            # Payment
            # ------------------------------------------

            "payment_method",
            "provider",
            "status",

            # ------------------------------------------
            # Amount
            # ------------------------------------------

            "amount",
            "currency",

            # ------------------------------------------
            # References
            # ------------------------------------------

            "reference",
            "provider_reference",

            # ------------------------------------------
            # Gateway
            # ------------------------------------------

            "gateway_response",
            "failure_reason",

            # ------------------------------------------
            # Lifecycle
            # ------------------------------------------

            "paid_at",
            "refunded_at",

            # ------------------------------------------
            # Timestamps
            # ------------------------------------------

            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


# ==================================================
# Order Fulfillment Serializer
# ==================================================

class OrderFulfillmentSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only representation of one store's fulfillment
    within an Order.

    A single Order can contain multiple fulfillments:

        Order
          ├── Fulfillment A → Store A → Rider A
          ├── Fulfillment B → Store B → Rider B
          └── Fulfillment C → Store C → Rider C

    Dispatch updates the fulfillment lifecycle after
    checkout.
    """

    # ==================================================
    # Computed Fields
    # ==================================================

    has_rider = serializers.BooleanField(
        read_only=True,
    )

    pickup_location = serializers.ReadOnlyField()

    delivery_location = serializers.ReadOnlyField()

    can_dispatch = serializers.BooleanField(
        read_only=True,
    )

    is_delivered = serializers.BooleanField(
        read_only=True,
    )

    is_cancelled = serializers.BooleanField(
        read_only=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        model = OrderFulfillment

        fields = [
            # ------------------------------------------
            # Identity
            # ------------------------------------------

            "id",
            "order",
            "store",
            "vendor",

            # ------------------------------------------
            # Rider / Dispatch
            # ------------------------------------------

            "rider",
            "assignment",

            # ------------------------------------------
            # Status
            # ------------------------------------------

            "status",

            # ------------------------------------------
            # Store Snapshot
            # ------------------------------------------

            "store_name",
            "store_address_line_1",
            "store_address_line_2",
            "store_city",
            "store_state",
            "store_country",
            "store_postal_code",

            "store_latitude",
            "store_longitude",

            "store_pickup_instructions",
            "store_preparation_time_minutes",

            # ------------------------------------------
            # Fulfillment Pricing
            # ------------------------------------------

            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "tax_amount",
            "total_amount",

            # ------------------------------------------
            # Delivery Destination
            # ------------------------------------------

            "delivery_address_line_1",
            "delivery_address_line_2",
            "delivery_city",
            "delivery_state",
            "delivery_country",
            "delivery_postal_code",

            "delivery_latitude",
            "delivery_longitude",

            "delivery_instructions",

            # ------------------------------------------
            # Tracking
            # ------------------------------------------

            "estimated_delivery_at",
            "picked_up_at",
            "delivered_at",
            "cancelled_at",

            # ------------------------------------------
            # Computed
            # ------------------------------------------

            "has_rider",
            "pickup_location",
            "delivery_location",
            "can_dispatch",
            "is_delivered",
            "is_cancelled",

            # ------------------------------------------
            # Timestamps
            # ------------------------------------------

            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


# ==================================================
# Order Serializer
# ==================================================

class OrderSerializer(
    serializers.ModelSerializer,
):
    """
    Complete read-only representation of an Order.

    Nested structure:

        Order
          │
          ├── Items
          │     ├── Product
          │     ├── Variant
          │     └── Store snapshot
          │
          ├── Addresses
          │     ├── Shipping
          │     └── Billing
          │
          ├── Payments
          │     ├── Payment attempt
          │     └── Payment history
          │
          └── Fulfillments
                ├── Store A
                ├── Store B
                └── Store C
    """

    # ==================================================
    # Nested Items
    # ==================================================

    items = OrderItemSerializer(
        many=True,
        read_only=True,
    )

    # ==================================================
    # Nested Addresses
    # ==================================================

    addresses = OrderAddressSerializer(
        many=True,
        read_only=True,
    )

    # ==================================================
    # Nested Payments
    # ==================================================

    payments = OrderPaymentSerializer(
        many=True,
        read_only=True,
    )

    # ==================================================
    # Nested Fulfillments
    # ==================================================

    fulfillments = OrderFulfillmentSerializer(
        many=True,
        read_only=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        model = Order

        fields = [
            # ------------------------------------------
            # Identity
            # ------------------------------------------

            "id",
            "customer",
            "order_number",

            # ------------------------------------------
            # Order Status
            # ------------------------------------------

            "status",
            "payment_status",
            "payment_method",

            # ------------------------------------------
            # Pricing
            # ------------------------------------------

            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "currency",

            # ------------------------------------------
            # Customer Note
            # ------------------------------------------

            "customer_note",

            # ------------------------------------------
            # Nested Resources
            # ------------------------------------------

            "items",
            "addresses",
            "payments",
            "fulfillments",

            # ------------------------------------------
            # Lifecycle
            # ------------------------------------------

            "confirmed_at",
            "paid_at",
            "delivered_at",
            "cancelled_at",

            # ------------------------------------------
            # Timestamps
            # ------------------------------------------

            "created_at",
            "updated_at",
        ]

        read_only_fields = fields