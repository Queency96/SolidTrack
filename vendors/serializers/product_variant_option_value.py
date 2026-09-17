from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from vendors.models import (
    ProductOptionValue,
    ProductVariant,
)

from ..models.product_variant_option_value import (
    ProductVariantOptionValue,
)


# ============================================================
# Product Variant Option Value Serializer
# ============================================================

class ProductVariantOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for assigning a ProductOptionValue
    to a ProductVariant.

    The variant itself is supplied through serializer context:

        context={
            "variant": variant
        }

    The serializer validates:

        1. A variant is present.
        2. The selected option value exists.
        3. The option value belongs to the same product.
        4. The option is active.
        5. The option value is active.
        6. A variant cannot have multiple values for
           the same option.

    The actual lifecycle operation remains in the
    ProductVariantOptionValueService.
    """

    # ========================================================
    # Input
    # ========================================================

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

    # ========================================================
    # Display
    # ========================================================

    option = serializers.CharField(
        source="option_name",
        read_only=True,
    )

    value = serializers.CharField(
        source="value_name",
        read_only=True,
    )

    # --------------------------------------------------------
    # Explicit schema types for model properties
    # --------------------------------------------------------

    option_id = serializers.SerializerMethodField(
        read_only=True,
    )

    display_name = serializers.SerializerMethodField(
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
            # Option
            # ------------------------------------------------

            "option_id",
            "option",

            # ------------------------------------------------
            # Value
            # ------------------------------------------------

            "value",
            "display_name",

            # ------------------------------------------------
            # Timestamp
            # ------------------------------------------------

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

    # ========================================================
    # Schema-typed Model Properties
    # ========================================================

    @extend_schema_field(serializers.UUIDField())
    def get_option_id(self, obj):
        """
        Return the ProductOption UUID.

        ProductVariantOptionValue exposes option_id as a
        model property, so drf-spectacular cannot reliably
        infer its type from ReadOnlyField().
        """

        return obj.option_id

    # --------------------------------------------------------

    @extend_schema_field(serializers.CharField())
    def get_display_name(self, obj):
        """
        Return the human-readable option/value combination.

        Example:

            Color: Black
        """

        return obj.display_name

    # ========================================================
    # Validation
    # ========================================================

    def validate(self, attrs):
        """
        Validate the selected option value against the
        supplied variant.

        The variant is intentionally obtained from serializer
        context rather than accepting a writable `variant`
        field from the request.
        """

        variant = self.context.get("variant")

        option_value = attrs.get("option_value")

        # ----------------------------------------------------
        # Variant context
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