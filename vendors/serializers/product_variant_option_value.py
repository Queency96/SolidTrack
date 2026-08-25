from rest_framework import serializers
from ..models.product_variant_option_value import (
    ProductVariantOptionValue,
)
from vendors.models import (
    ProductOptionValue,
)


class ProductVariantOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for assigning a ProductOptionValue
    to a ProductVariant.
    """

    option_value_id = serializers.PrimaryKeyRelatedField(
        source="option_value",
        queryset=ProductOptionValue.objects.select_related(
            "option",
        ),
        write_only=True,
    )

    option = serializers.CharField(
        source="option_name",
        read_only=True,
    )

    value = serializers.CharField(
        source="value_name",
        read_only=True,
    )

    option_id = serializers.ReadOnlyField()

    display_name = serializers.ReadOnlyField()

    class Meta:
        model = ProductVariantOptionValue

        fields = [
            "id",
            "option_value_id",
            "option_id",
            "option",
            "value",
            "display_name",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "option_id",
            "option",
            "value",
            "display_name",
            "created_at",
        ]

    def validate(self, attrs):
        """
        Validate that the selected option value belongs
        to the same product as the variant.
        """

        variant = self.context.get(
            "variant"
        )

        option_value = attrs.get(
            "option_value"
        )

        if variant is None:
            raise serializers.ValidationError(
                {
                    "variant": (
                        "Variant context is required."
                    )
                }
            )

        if option_value is None:
            raise serializers.ValidationError(
                {
                    "option_value_id": (
                        "Option value is required."
                    )
                }
            )

        # ------------------------------------------
        # Product ownership
        # ------------------------------------------

        if (
            option_value.option.product_id
            != variant.product_id
        ):
            raise serializers.ValidationError(
                {
                    "option_value_id": (
                        "The selected option value "
                        "does not belong to the "
                        "variant's product."
                    )
                }
            )

        # ------------------------------------------
        # One value per option
        # ------------------------------------------

        existing = (
            ProductVariantOptionValue.objects
            .filter(
                variant=variant,
                option_value__option_id=(
                    option_value.option_id
                ),
            )
        )

        if self.instance:
            existing = existing.exclude(
                pk=self.instance.pk
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