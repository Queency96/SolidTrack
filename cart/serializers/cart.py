from rest_framework import serializers
from ..models import Cart
from .cart_item import (
    CartItemSerializer,
)


class CartSerializer(
    serializers.ModelSerializer,
):
    """
    Full customer cart representation.
    """

    # ==================================================
    # Items
    # ==================================================

    items = CartItemSerializer(
        many=True,
        read_only=True,
    )

    # ==================================================
    # Totals
    # ==================================================

    items_count = serializers.ReadOnlyField()

    total_items = serializers.ReadOnlyField()

    subtotal = serializers.ReadOnlyField()

    is_empty = serializers.ReadOnlyField()

    is_currently_active = serializers.ReadOnlyField()

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        model = Cart

        fields = [
            "id",
            "customer",

            "items",

            "items_count",
            "total_items",
            "subtotal",
            "is_empty",
            "is_currently_active",

            "is_active",

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "customer",

            "items",

            "items_count",
            "total_items",
            "subtotal",
            "is_empty",
            "is_currently_active",

            "is_active",

            "created_at",
            "updated_at",
        ]