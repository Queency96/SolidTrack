from rest_framework import serializers

from vendors.models import (
    ProductVariant,
    ProductVariantImage,
)

from vendors.serializers.product import (
    ProductVariantImageSerializer,
)

from .product_variant_option_value import (
    ProductVariantOptionValueSerializer,
)


# ============================================================
# Shared Variant Validation
# ============================================================

class ProductVariantValidationMixin:
    """
    Shared validation logic for ProductVariant create/update
    serializers.

    Business lifecycle operations such as:
        - assigning option values
        - creating variant images
        - changing default variants
        - deleting variants
        - stock/business rules

    should remain in the service layer where appropriate.
    """

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        # ----------------------------------------------------
        # Effective values
        # ----------------------------------------------------

        price = attrs.get(
            "price",
            getattr(instance, "price", None),
        )

        compare_at_price = attrs.get(
            "compare_at_price",
            getattr(instance, "compare_at_price", None),
        )

        weight = attrs.get(
            "weight",
            getattr(instance, "weight", None),
        )

        stock_quantity = attrs.get(
            "stock_quantity",
            getattr(instance, "stock_quantity", 0),
        )

        # ----------------------------------------------------
        # Price
        # ----------------------------------------------------

        if price is not None and price < 0:
            raise serializers.ValidationError(
                {
                    "price": (
                        "Variant price cannot be negative."
                    )
                }
            )

        # ----------------------------------------------------
        # Compare-at price
        # ----------------------------------------------------

        if (
            compare_at_price is not None
            and price is not None
            and compare_at_price < price
        ):
            raise serializers.ValidationError(
                {
                    "compare_at_price": (
                        "Compare-at price cannot be lower "
                        "than the variant price."
                    )
                }
            )

        # ----------------------------------------------------
        # Weight
        # ----------------------------------------------------

        if weight is not None and weight < 0:
            raise serializers.ValidationError(
                {
                    "weight": (
                        "Weight cannot be negative."
                    )
                }
            )

        # ----------------------------------------------------
        # Stock
        # ----------------------------------------------------

        if (
            stock_quantity is not None
            and stock_quantity < 0
        ):
            raise serializers.ValidationError(
                {
                    "stock_quantity": (
                        "Stock quantity cannot be negative."
                    )
                }
            )

        return attrs


# ============================================================
# Product Variant Serializer
# ============================================================

class ProductVariantSerializer(
    ProductVariantValidationMixin,
    serializers.ModelSerializer,
):
    """
    Serializer for retrieving/displaying a ProductVariant.

    Option values and images are read-only representations.

    They should be managed through:

        ProductVariantOptionValueService
        ProductVariantImageService
    """

    # ========================================================
    # Computed Fields
    # ========================================================

    effective_price = serializers.ReadOnlyField()

    effective_compare_at_price = (
        serializers.ReadOnlyField()
    )

    is_in_stock = serializers.ReadOnlyField()

    can_be_purchased = serializers.ReadOnlyField()

    has_options = serializers.ReadOnlyField()

    option_value_count = serializers.ReadOnlyField()

    option_count = serializers.ReadOnlyField()

    option_summary = serializers.ReadOnlyField()

    # ========================================================
    # Pickup
    # ========================================================

    pickup_store_id = serializers.ReadOnlyField(
        source="product.store_id",
    )

    pickup_location = serializers.ReadOnlyField()

    # ========================================================
    # Selected Option Values
    # ========================================================

    selected_option_values = (
        serializers.SerializerMethodField()
    )

    # ========================================================
    # Variant Images
    # ========================================================

    images = serializers.SerializerMethodField()

    # ========================================================
    # Primary Image
    # ========================================================

    primary_image = serializers.SerializerMethodField()

    # ========================================================
    # Meta
    # ========================================================

    class Meta:
        model = ProductVariant

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",
            "product",
            "name",
            "sku",

            # ------------------------------------------------
            # Options
            # ------------------------------------------------

            "selected_option_values",
            "option_summary",
            "option_value_count",
            "option_count",
            "has_options",

            # ------------------------------------------------
            # Images
            # ------------------------------------------------

            "images",
            "primary_image",

            # ------------------------------------------------
            # Pricing
            # ------------------------------------------------

            "price",
            "compare_at_price",
            "effective_price",
            "effective_compare_at_price",

            # ------------------------------------------------
            # Inventory
            # ------------------------------------------------

            "stock_quantity",
            "track_inventory",
            "is_in_stock",

            # ------------------------------------------------
            # Physical
            # ------------------------------------------------

            "weight",

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            "is_active",
            "is_default",
            "is_available",
            "can_be_purchased",

            # ------------------------------------------------
            # Ordering
            # ------------------------------------------------

            "sort_order",

            # ------------------------------------------------
            # Pickup
            # ------------------------------------------------

            "pickup_store_id",
            "pickup_location",

            # ------------------------------------------------
            # Timestamps
            # ------------------------------------------------

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            # Identity
            "id",
            "product",

            # Options
            "selected_option_values",
            "option_summary",
            "option_value_count",
            "option_count",
            "has_options",

            # Images
            "images",
            "primary_image",

            # Effective pricing
            "effective_price",
            "effective_compare_at_price",

            # Inventory
            "is_in_stock",

            # Purchase
            "can_be_purchased",

            # Pickup
            "pickup_store_id",
            "pickup_location",

            # Timestamps
            "created_at",
            "updated_at",
        ]

    # ========================================================
    # Selected Option Values
    # ========================================================

    def get_selected_option_values(self, obj):
        """
        Return the option values assigned to this variant.

        Uses a prefetched collection when available.

        Expected queryset optimization:

            Prefetch(
                "variant_option_values",
                queryset=...,
                to_attr="_prefetched_variant_option_links",
            )
        """

        links = getattr(
            obj,
            "_prefetched_variant_option_links",
            None,
        )

        if links is None:
            links = (
                obj.variant_option_values
                .select_related(
                    "option_value",
                    "option_value__option",
                )
                .all()
            )

        return ProductVariantOptionValueSerializer(
            links,
            many=True,
            context=self.context,
        ).data

    # ========================================================
    # Images
    # ========================================================

    def get_images(self, obj):
        """
        Return variant images.

        If the queryset provides:

            _prefetched_variant_images

        no additional database query is performed.
        """

        images = getattr(
            obj,
            "_prefetched_variant_images",
            None,
        )

        if images is None:
            images = (
                obj.images
                .filter(is_active=True)
                .order_by(
                    "-is_primary",
                    "display_order",
                    "created_at",
                )
            )

        return ProductVariantImageSerializer(
            images,
            many=True,
            context=self.context,
        ).data

    # ========================================================
    # Primary Image
    # ========================================================

    def get_primary_image(self, obj):
        """
        Return the primary active image.

        Uses the same prefetched image collection used by
        get_images(), preventing another database query.
        """

        images = getattr(
            obj,
            "_prefetched_variant_images",
            None,
        )

        if images is None:
            images = (
                obj.images
                .filter(is_active=True)
                .order_by(
                    "-is_primary",
                    "display_order",
                    "created_at",
                )
            )

        image = next(iter(images), None)

        if image is None:
            return None

        return ProductVariantImageSerializer(
            image,
            context=self.context,
        ).data


# ============================================================
# Product Variant Create Serializer
# ============================================================

class ProductVariantCreateSerializer(
    ProductVariantValidationMixin,
    serializers.ModelSerializer,
):
    """
    Serializer for creating a ProductVariant.

    Product assignment is controlled by the view/service.

    Option values and images are intentionally excluded from
    creation.

    They should be handled by:

        ProductVariantService
        ProductVariantOptionValueService
        ProductVariantImageService
    """

    class Meta:
        model = ProductVariant

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",
            "product",
            "name",
            "sku",

            # ------------------------------------------------
            # Pricing
            # ------------------------------------------------

            "price",
            "compare_at_price",

            # ------------------------------------------------
            # Inventory
            # ------------------------------------------------

            "stock_quantity",
            "track_inventory",

            # ------------------------------------------------
            # Physical
            # ------------------------------------------------

            "weight",

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            "is_active",
            "is_default",

            # ------------------------------------------------
            # Ordering
            # ------------------------------------------------

            "sort_order",

            # ------------------------------------------------
            # Availability
            # ------------------------------------------------

            "is_available",

            # ------------------------------------------------
            # Timestamps
            # ------------------------------------------------

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "product",
            "is_available",
            "created_at",
            "updated_at",
        ]


# ============================================================
# Product Variant Update Serializer
# ============================================================

class ProductVariantUpdateSerializer(
    ProductVariantValidationMixin,
    serializers.ModelSerializer,
):
    """
    Serializer for updating an existing ProductVariant.

    Product ownership cannot be changed through this serializer.

    Changes involving:
        - option values
        - images
        - default-variant lifecycle
        - complex inventory operations

    should be handled by the appropriate service.
    """

    class Meta:
        model = ProductVariant

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",
            "product",
            "name",
            "sku",

            # ------------------------------------------------
            # Pricing
            # ------------------------------------------------

            "price",
            "compare_at_price",

            # ------------------------------------------------
            # Inventory
            # ------------------------------------------------

            "stock_quantity",
            "track_inventory",

            # ------------------------------------------------
            # Physical
            # ------------------------------------------------

            "weight",

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            "is_active",
            "is_default",

            # ------------------------------------------------
            # Ordering
            # ------------------------------------------------

            "sort_order",

            # ------------------------------------------------
            # Availability
            # ------------------------------------------------

            "is_available",

            # ------------------------------------------------
            # Timestamps
            # ------------------------------------------------

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "product",
            "is_available",
            "created_at",
            "updated_at",
        ]