from rest_framework import serializers

from vendors.models import (
    ProductOption,
    ProductOptionValue,
    ProductVariant,
)
from vendors.models.product_variant_option_value import (
    ProductVariantOptionValue,
)


# ============================================================
# Product Option Value Serializer
# ============================================================

class ProductOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for ProductOptionValue.

    Used primarily for vendor/internal product management
    and product option representations.

    Variant statistics and availability are read-only
    computed properties from the model.
    """

    option_name = serializers.CharField(
        source="option.name",
        read_only=True,
    )

    product_id = serializers.UUIDField(
        source="option.product_id",
        read_only=True,
    )

    variant_count = serializers.IntegerField(
        read_only=True,
    )

    active_variant_count = serializers.IntegerField(
        read_only=True,
    )

    is_available = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = ProductOptionValue

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",

            # ------------------------------------------------
            # Option
            # ------------------------------------------------

            "option",
            "option_name",
            "product_id",

            # ------------------------------------------------
            # Value
            # ------------------------------------------------

            "name",
            "slug",
            "sort_order",
            "is_active",

            # ------------------------------------------------
            # Computed
            # ------------------------------------------------

            "is_available",
            "variant_count",
            "active_variant_count",
        ]

        read_only_fields = [
            "id",
            "option_name",
            "product_id",
            "is_available",
            "variant_count",
            "active_variant_count",
        ]


# ============================================================
# Public Product Option Value Serializer
# ============================================================

class PublicProductOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only ProductOptionValue representation for customers.

    Only public-facing information is exposed.
    """

    is_available = serializers.ReadOnlyField()

    class Meta:
        model = ProductOptionValue

        fields = [
            "id",
            "name",
            "slug",
            "sort_order",
            "is_available",
        ]

        read_only_fields = fields


# ============================================================
# Product Option Serializer
# ============================================================

class ProductOptionSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for ProductOption.

    Option values are nested read-only representations.

    Creating/updating option values should be handled through
    the appropriate service or dedicated endpoint.
    """

    values = ProductOptionValueSerializer(
        many=True,
        read_only=True,
    )

    value_count = serializers.IntegerField(
        read_only=True,
    )

    active_value_count = serializers.IntegerField(
        read_only=True,
    )

    has_values = serializers.BooleanField(
        read_only=True,
    )

    has_active_values = serializers.BooleanField(
        read_only=True,
    )

    variant_count = serializers.IntegerField(
        read_only=True,
    )

    class Meta:
        model = ProductOption

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",
            "product",

            # ------------------------------------------------
            # Option
            # ------------------------------------------------

            "name",
            "slug",
            "sort_order",
            "is_active",

            # ------------------------------------------------
            # Values
            # ------------------------------------------------

            "values",

            # ------------------------------------------------
            # Computed
            # ------------------------------------------------

            "value_count",
            "active_value_count",
            "has_values",
            "has_active_values",
            "variant_count",
        ]

        read_only_fields = [
            "id",
            "value_count",
            "active_value_count",
            "has_values",
            "has_active_values",
            "variant_count",
        ]


# ============================================================
# Public Product Option Serializer
# ============================================================

class PublicProductOptionSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only ProductOption representation for customers.

    Only active option values are exposed.
    """

    values = serializers.SerializerMethodField()

    class Meta:
        model = ProductOption

        fields = [
            "id",
            "name",
            "slug",
            "sort_order",
            "values",
        ]

        read_only_fields = fields

    def get_values(self, obj):
        """
        Return only active option values.

        If values have already been prefetched with a filtered
        queryset, use the prefetched collection to avoid an
        additional query.
        """

        values = getattr(
            obj,
            "_prefetched_active_values",
            None,
        )

        if values is None:
            values = (
                obj.values
                .filter(
                    is_active=True,
                )
                .order_by(
                    "sort_order",
                    "name",
                )
            )

        return PublicProductOptionValueSerializer(
            values,
            many=True,
            context=self.context,
        ).data


# ============================================================
# Product Variant Option Value Assignment Serializer
# ============================================================

class ProductVariantOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for assigning a ProductOptionValue
    to a ProductVariant.

    The variant should normally be supplied through serializer
    context:

        context={
            "variant": variant,
        }

    The client should not be allowed to change the variant
    relationship through the request payload.
    """

    option_value_id = serializers.PrimaryKeyRelatedField(
        source="option_value",
        queryset=(
            ProductOptionValue.objects
            .select_related(
                "option",
                "option__product",
            )
        ),
        write_only=True,
    )

    option_name = serializers.CharField(
        source="option.name",
        read_only=True,
    )

    value_name = serializers.CharField(
        source="option_value.name",
        read_only=True,
    )

    display_name = serializers.ReadOnlyField()

    product_id = serializers.UUIDField(
        source="product_id",
        read_only=True,
    )

    # ========================================================
    # Meta
    # ========================================================

    class Meta:
        model = ProductVariantOptionValue

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",

            # ------------------------------------------------
            # Input
            # ------------------------------------------------

            "option_value_id",

            # ------------------------------------------------
            # Display
            # ------------------------------------------------

            "option_name",
            "value_name",
            "display_name",

            # ------------------------------------------------
            # Product
            # ------------------------------------------------

            "product_id",

            # ------------------------------------------------
            # Timestamp
            # ------------------------------------------------

            "created_at",
        ]

        read_only_fields = [
            "id",
            "option_name",
            "value_name",
            "display_name",
            "product_id",
            "created_at",
        ]

    # ========================================================
    # Validation
    # ========================================================

    def validate(self, attrs):
        """
        Validate the option value against the variant supplied
        through serializer context.
        """

        variant = self.context.get(
            "variant",
        )

        option_value = attrs.get(
            "option_value",
        )

        # ----------------------------------------------------
        # Variant
        # ----------------------------------------------------

        if variant is None:
            raise serializers.ValidationError(
                {
                    "variant": (
                        "Variant context is required."
                    )
                }
            )

        if not isinstance(
            variant,
            ProductVariant,
        ):
            raise serializers.ValidationError(
                {
                    "variant": (
                        "Invalid variant context."
                    )
                }
            )

        # ----------------------------------------------------
        # Option value
        # ----------------------------------------------------

        if option_value is None:
            raise serializers.ValidationError(
                {
                    "option_value_id": (
                        "Option value is required."
                    )
                }
            )

        # ----------------------------------------------------
        # Related option
        # ----------------------------------------------------

        option = option_value.option

        if option is None:
            raise serializers.ValidationError(
                {
                    "option_value_id": (
                        "The selected option value "
                        "has no associated option."
                    )
                }
            )

        # ----------------------------------------------------
        # Product ownership
        # ----------------------------------------------------

        if option.product_id != variant.product_id:
            raise serializers.ValidationError(
                {
                    "option_value_id": (
                        "The selected option value "
                        "does not belong to the "
                        "variant's product."
                    )
                }
            )

        # ----------------------------------------------------
        # Option status
        # ----------------------------------------------------

        if not option.is_active:
            raise serializers.ValidationError(
                {
                    "option_value_id": (
                        "The selected option is inactive."
                    )
                }
            )

        # ----------------------------------------------------
        # Option value status
        # ----------------------------------------------------

        if not option_value.is_active:
            raise serializers.ValidationError(
                {
                    "option_value_id": (
                        "The selected option value "
                        "is inactive."
                    )
                }
            )

        # ----------------------------------------------------
        # One value per option
        # ----------------------------------------------------

        existing = (
            ProductVariantOptionValue.objects
            .filter(
                variant_id=variant.pk,
                option_value__option_id=option.pk,
            )
        )

        # ----------------------------------------------------
        # Exclude current record during update
        # ----------------------------------------------------

        if self.instance is not None:
            existing = existing.exclude(
                pk=self.instance.pk,
            )

        if existing.exists():
            raise serializers.ValidationError(
                {
                    "option_value_id": (
                        "This variant already has "
                        "a value for this option."
                    )
                }
            )

        return attrs


# ============================================================
# Product Variant Option Value Nested Serializer
# ============================================================

class ProductVariantOptionValueNestedSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only representation used inside ProductVariant
    responses.

    This serializer is intentionally lightweight because it is
    commonly rendered as part of a product/variant response.
    """

    option = serializers.CharField(
        source="option.name",
        read_only=True,
    )

    value = serializers.CharField(
        source="option_value.name",
        read_only=True,
    )

    display_name = serializers.ReadOnlyField()

    class Meta:
        model = ProductVariantOptionValue

        fields = [
            "id",
            "option",
            "value",
            "display_name",
        ]

        read_only_fields = fields