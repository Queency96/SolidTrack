from rest_framework import serializers
from ..models import (
    ProductOption,
    ProductOptionValue,
)
from vendors.models.product_variant_option_value import ProductVariantOptionValue



# ==================================================
# Product Option Value
# ==================================================

class ProductOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for ProductOptionValue.
    """

    product_id = serializers.ReadOnlyField(
        source="product_id",
    )

    is_available = serializers.ReadOnlyField()

    class Meta:

        model = ProductOptionValue

        fields = [
            "id",
            "option",
            "name",
            "slug",
            "sort_order",
            "is_active",
            "product_id",
            "is_available",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "product_id",
            "is_available",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Option value name cannot be empty."
            )

        return value

    def validate_option(self, option):

        if option is None:
            raise serializers.ValidationError(
                "Option is required."
            )

        return option


# ==================================================
# Public Product Option Value
# ==================================================

class PublicProductOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only serializer used by customers.
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


# ==================================================
# Product Option
# ==================================================

class ProductOptionSerializer(
    serializers.ModelSerializer,
):
    """
    Full serializer for managing ProductOption.

    Option values are represented separately because
    ProductOptionValue has its own lifecycle.
    """

    value_count = serializers.ReadOnlyField()

    active_value_count = serializers.ReadOnlyField()

    has_values = serializers.ReadOnlyField()

    active_values = serializers.SerializerMethodField()

    class Meta:

        model = ProductOption

        fields = [
            "id",
            "product",
            "name",
            "slug",
            "sort_order",
            "is_active",
            "value_count",
            "active_value_count",
            "has_values",
            "active_values",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "value_count",
            "active_value_count",
            "has_values",
            "active_values",
            "created_at",
            "updated_at",
        ]

    def get_active_values(self, obj):

        queryset = (
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
            queryset,
            many=True,
        ).data

    def validate_name(self, value):

        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Option name cannot be empty."
            )

        return value


# ==================================================
# Public Product Option
# ==================================================

class PublicProductOptionSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only option representation for customers.
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

        queryset = (
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
            queryset,
            many=True,
        ).data




class ProductVariantOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for assigning a ProductOptionValue
    to a ProductVariant.
    """

    option_name = serializers.ReadOnlyField(
        source="option.name",
    )

    value_name = serializers.ReadOnlyField(
        source="option_value.name",
    )

    display_name = serializers.ReadOnlyField()

    product_id = serializers.ReadOnlyField(
        source="product.id",
    )

    class Meta:

        model = ProductVariantOptionValue

        fields = [
            "id",
            "variant",
            "option_value",
            "option_name",
            "value_name",
            "display_name",
            "product_id",
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

    def validate(self, attrs):

        variant = attrs.get(
            "variant",
        )

        option_value = attrs.get(
            "option_value",
        )

        if variant is None:
            raise serializers.ValidationError(
                {
                    "variant": (
                        "Variant is required."
                    )
                }
            )

        if option_value is None:
            raise serializers.ValidationError(
                {
                    "option_value": (
                        "Option value is required."
                    )
                }
            )

        # ------------------------------------------
        # Product ownership
        # ------------------------------------------

        if (
            variant.product_id
            != option_value.option.product_id
        ):

            raise serializers.ValidationError(
                {
                    "option_value": (
                        "The selected option value "
                        "does not belong to the "
                        "variant's product."
                    )
                }
            )

        # ------------------------------------------
        # One value per option
        # ------------------------------------------

        queryset = (
            ProductVariantOptionValue.objects
            .filter(
                variant=variant,
                option_value__option=(
                    option_value.option
                ),
            )
        )

        if self.instance:

            queryset = queryset.exclude(
                pk=self.instance.pk,
            )

        if queryset.exists():

            raise serializers.ValidationError(
                {
                    "option_value": (
                        "This variant already has "
                        "a value for this option."
                    )
                }
            )

        return attrs




class ProductVariantOptionValueNestedSerializer(
    serializers.ModelSerializer,
):
    """
    Read-only representation used inside
    ProductVariant responses.
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