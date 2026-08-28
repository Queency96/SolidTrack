from rest_framework import serializers
from order.models import (
    OrderPayment,
)




# ==================================================
# Order Payment Serializer
# ==================================================

class OrderPaymentSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for an OrderPayment.

    Payment records are historical transaction records
    and therefore read-only through the order API.
    """

    class Meta:
        model = OrderPayment

        fields = [
            "id",

            # Payment
            "payment_method",
            "provider",
            "status",

            # Financial
            "amount",
            "currency",

            # References
            "reference",
            "provider_reference",

            # Gateway
            "gateway_response",
            "failure_reason",

            # Timestamps
            "paid_at",
            "refunded_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


