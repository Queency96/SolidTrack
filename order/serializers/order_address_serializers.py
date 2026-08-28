from rest_framework import serializers
from order.models import (
    OrderAddress,
)




# ==================================================
# Order Address Serializer
# ==================================================

class OrderAddressSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for an immutable OrderAddress snapshot.

    This represents the address used by the order at the
    time of checkout.

    It must not expose a writable interface because changing
    an historical order address would corrupt order history.
    """

    class Meta:
        model = OrderAddress

        fields = [
            "id",

            # Address type
            "address_type",

            # Recipient
            "recipient_name",
            "phone_number",

            # Address
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "country",
            "postal_code",
            "landmark",

            # Coordinates
            "latitude",
            "longitude",
        ]

        read_only_fields = fields

