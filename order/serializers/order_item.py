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
    Serializer for an OrderItem.

    OrderItem contains historical product, variant,
    store, quantity, and pricing snapshots.
    """

    class Meta:
        model = OrderItem

        fields = [
            "id",

            # Relationships
            "product",
            "variant",
            "store",
            "fulfillment",

            # Product snapshot
            "product_name",
            "product_sku",

            # Variant snapshot
            "variant_name",
            "variant_sku",
            "option_summary",

            # Store snapshot
            "store_name",
            "store_address_line_1",
            "store_address_line_2",
            "store_city",
            "store_state",
            "store_country",
            "store_postal_code",
            "store_latitude",
            "store_longitude",

            # Financial snapshot
            "unit_price",
            "quantity",
            "subtotal",
            "currency",
        ]

        read_only_fields = fields

