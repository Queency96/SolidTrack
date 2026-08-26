from rest_framework import serializers
from ..models import CartItem


class CartItemSerializer(
    serializers.ModelSerializer,
):
    """
    Full read-only representation of a cart item.

    Supports:

        Product without variant

    and:

        Product + ProductVariant
    """

    # ==================================================
    # Product
    # ==================================================

    product_name = serializers.ReadOnlyField(
        source="product.name",
    )

    # ==================================================
    # Variant
    # ==================================================

    variant_name = serializers.ReadOnlyField(
        source="variant.name",
    )

    variant_sku = serializers.ReadOnlyField(
        source="variant.sku",
    )

    option_summary = serializers.ReadOnlyField(
        source="variant.option_summary",
    )

    # ==================================================
    # Pricing
    # ==================================================

    subtotal = serializers.ReadOnlyField()

    # ==================================================
    # Availability
    # ==================================================

    is_available = serializers.ReadOnlyField()

    # ==================================================
    # Inventory
    # ==================================================

    tracks_inventory = serializers.ReadOnlyField()

    available_stock = serializers.ReadOnlyField()

    has_sufficient_stock = serializers.ReadOnlyField()

    # ==================================================
    # Variant State
    # ==================================================

    has_variant = serializers.ReadOnlyField()

    # ==================================================
    # Image
    # ==================================================

    primary_image = serializers.SerializerMethodField()

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        model = CartItem

        fields = [
            "id",

            "cart",

            # Product
            "product",
            "product_name",

            # Variant
            "variant",
            "variant_name",
            "variant_sku",
            "option_summary",

            # Quantity
            "quantity",

            # Pricing
            "unit_price",
            "subtotal",

            # Image
            "primary_image",

            # Availability
            "is_available",

            # Inventory
            "tracks_inventory",
            "available_stock",
            "has_sufficient_stock",

            # Variant state
            "has_variant",

            # Timestamps
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "cart",

            "product_name",

            "variant_name",
            "variant_sku",
            "option_summary",

            "unit_price",
            "subtotal",

            "primary_image",

            "is_available",

            "tracks_inventory",
            "available_stock",
            "has_sufficient_stock",

            "has_variant",

            "created_at",
            "updated_at",
        ]

    # ==================================================
    # Primary Image
    # ==================================================

    def get_primary_image(
        self,
        obj,
    ):
        """
        Return the most appropriate primary image.

        Priority:

            1. Variant primary image
            2. Product primary image
            3. None
        """

        image = obj.primary_image

        if image is None:
            return None

        request = self.context.get(
            "request",
        )

        if request:

            return request.build_absolute_uri(
                image.image.url,
            )

        return image.image.url