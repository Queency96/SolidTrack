from rest_framework import serializers

from vendors.models import ProductVariant

from .product_variant_option_value import (
    ProductVariantOptionValueSerializer,
)


class ProductVariantSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for ProductVariant.

    Used primarily for retrieving/displaying variants.
    """

    # ==================================================
    # Computed Fields
    # ==================================================

    effective_price = serializers.ReadOnlyField()

    effective_compare_at_price = (
        serializers.ReadOnlyField()
    )

    is_in_stock = serializers.ReadOnlyField()

    is_available = serializers.ReadOnlyField()

    has_options = serializers.ReadOnlyField()

    option_value_count = serializers.ReadOnlyField()

    option_count = serializers.ReadOnlyField()

    option_summary = serializers.ReadOnlyField()

    # ==================================================
    # Pickup
    # ==================================================

    pickup_store_id = serializers.ReadOnlyField(
        source="pickup_store.id",
    )

    # ==================================================
    # Option Values
    # ==================================================

    selected_option_values = (
        ProductVariantOptionValueSerializer(
            source="variant_option_values",
            many=True,
            read_only=True,
        )
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:
        model = ProductVariant

        fields = [
            # Identity
            "id",
            "product",
            "name",
            "sku",

            # Options
            "selected_option_values",
            "option_summary",
            "option_value_count",
            "option_count",
            "has_options",

            # Pricing
            "price",
            "compare_at_price",
            "effective_price",
            "effective_compare_at_price",

            # Inventory
            "stock_quantity",
            "track_inventory",
            "is_in_stock",

            # Physical
            "weight",

            # Status
            "is_active",
            "is_default",
            "is_available",

            # Ordering
            "sort_order",

            # Pickup
            "pickup_store_id",

            # Timestamps
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",

            "effective_price",
            "effective_compare_at_price",

            "is_in_stock",
            "is_available",

            "has_options",
            "option_value_count",
            "option_count",
            "option_summary",

            "selected_option_values",

            "pickup_store_id",

            "created_at",
            "updated_at",
        ]

    # ==================================================
    # Validation
    # ==================================================

    def validate(self, attrs):
        price = attrs.get(
            "price",
            getattr(
                self.instance,
                "price",
                None,
            ),
        )

        compare_at_price = attrs.get(
            "compare_at_price",
            getattr(
                self.instance,
                "compare_at_price",
                None,
            ),
        )

        weight = attrs.get(
            "weight",
            getattr(
                self.instance,
                "weight",
                None,
            ),
        )

        # ------------------------------------------
        # Price
        # ------------------------------------------

        if (
            price is not None
            and price < 0
        ):
            raise serializers.ValidationError(
                {
                    "price": (
                        "Variant price cannot "
                        "be negative."
                    )
                }
            )

        # ------------------------------------------
        # Compare-at price
        # ------------------------------------------

        if (
            compare_at_price is not None
            and price is not None
            and compare_at_price < price
        ):
            raise serializers.ValidationError(
                {
                    "compare_at_price": (
                        "Compare-at price cannot "
                        "be lower than the variant "
                        "price."
                    )
                }
            )

        # ------------------------------------------
        # Weight
        # ------------------------------------------

        if (
            weight is not None
            and weight < 0
        ):
            raise serializers.ValidationError(
                {
                    "weight": (
                        "Weight cannot be negative."
                    )
                }
            )

        return attrs






class ProductVariantCreateSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for creating a ProductVariant.

    The product is assigned by the view and should not
    be supplied by the client.
    """

    class Meta:
        model = ProductVariant

        fields = [
            "id",
            "product",
            "name",
            "sku",

            "price",
            "compare_at_price",

            "stock_quantity",
            "track_inventory",

            "weight",

            "is_active",
            "is_default",

            "sort_order",

            "pickup_store",
        ]

        read_only_fields = [
            "id",
            "product",
        ]

    def validate(self, attrs):

        price = attrs.get("price")

        compare_at_price = attrs.get(
            "compare_at_price"
        )

        weight = attrs.get("weight")

        if (
            price is not None
            and price < 0
        ):
            raise serializers.ValidationError(
                {
                    "price": (
                        "Variant price cannot "
                        "be negative."
                    )
                }
            )

        if (
            compare_at_price is not None
            and price is not None
            and compare_at_price < price
        ):
            raise serializers.ValidationError(
                {
                    "compare_at_price": (
                        "Compare-at price cannot "
                        "be lower than the variant "
                        "price."
                    )
                }
            )

        if (
            weight is not None
            and weight < 0
        ):
            raise serializers.ValidationError(
                {
                    "weight": (
                        "Weight cannot be negative."
                    )
                }
            )

        return attrs





class ProductVariantUpdateSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for updating an existing ProductVariant.
    """

    class Meta:
        model = ProductVariant

        fields = [
            "id",
            "product",
            "name",
            "sku",

            "price",
            "compare_at_price",

            "stock_quantity",
            "track_inventory",

            "weight",

            "is_active",
            "is_default",

            "sort_order",

            "pickup_store",
        ]

        read_only_fields = [
            "id",
            "product",
        ]

    def validate(self, attrs):

        price = attrs.get(
            "price",
            self.instance.price,
        )

        compare_at_price = attrs.get(
            "compare_at_price",
            self.instance.compare_at_price,
        )

        weight = attrs.get(
            "weight",
            self.instance.weight,
        )

        if (
            price is not None
            and price < 0
        ):
            raise serializers.ValidationError(
                {
                    "price": (
                        "Variant price cannot "
                        "be negative."
                    )
                }
            )

        if (
            compare_at_price is not None
            and price is not None
            and compare_at_price < price
        ):
            raise serializers.ValidationError(
                {
                    "compare_at_price": (
                        "Compare-at price cannot "
                        "be lower than the variant "
                        "price."
                    )
                }
            )

        if (
            weight is not None
            and weight < 0
        ):
            raise serializers.ValidationError(
                {
                    "weight": (
                        "Weight cannot be negative."
                    )
                }
            )

        return attrs