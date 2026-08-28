from rest_framework import serializers
from order.models import (
    OrderFulfillment,
)



# ==================================================
# Order Fulfillment Serializer
# ==================================================

class OrderFulfillmentSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for one store's fulfillment.

    A single Order may contain multiple fulfillments,
    with each fulfillment representing an independent
    store → customer delivery workflow.
    """

    class Meta:
        model = OrderFulfillment

        fields = [
            "id",

            # Relationships
            "store",
            "vendor",
            "rider",
            "assignment",

            # Status
            "status",

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
            "store_pickup_instructions",
            "store_preparation_time_minutes",

            # Pricing
            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "tax_amount",
            "total_amount",

            # Delivery destination
            "delivery_address_line_1",
            "delivery_address_line_2",
            "delivery_city",
            "delivery_state",
            "delivery_country",
            "delivery_postal_code",
            "delivery_latitude",
            "delivery_longitude",
            "delivery_instructions",

            # Tracking
            "estimated_delivery_at",
            "picked_up_at",
            "delivered_at",
            "cancelled_at",

            # Timestamps
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

