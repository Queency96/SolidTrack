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
            "order",
            "store",
            "store_contact_name",
            "store_contact_phone",

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

            # Pricing
            "subtotal",
            "delivery_fee",
            "service_fee",
            "insurance_fee",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "currency",

            # Notes
            "vendor_note",
            "preparation_note",

            # Timestamps
            "created_at",
            "updated_at",
            "processing_at",
            "packing_at",
            "ready_for_dispatch_at",
            "dispatched_at",
            "delivered_at",
            "cancelled_at",
            "out_for_delivery_at",
        ]

        read_only_fields = fields

