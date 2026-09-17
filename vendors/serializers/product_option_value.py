from rest_framework import serializers

from vendors.models import ProductOptionValue


# ============================================================
# Product Option Value Serializer
# ============================================================

class ProductOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for selectable ProductOptionValue records.

    Example:

        Color
            ├── Black
            ├── White
            └── Blue

    The option relationship is read-only.

    ProductOptionValue lifecycle operations should be handled
    through the appropriate service/view rather than allowing
    the client to move a value between options arbitrarily.
    """

    # ========================================================
    # Related Product
    # ========================================================

    product_id = serializers.UUIDField(
        source="option.product_id",
        read_only=True,
    )

    # ========================================================
    # Availability
    # ========================================================

    is_available = serializers.BooleanField(
        read_only=True,
    )

    # ========================================================
    # Meta
    # ========================================================

    class Meta:
        model = ProductOptionValue

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",

            # ------------------------------------------------
            # Relationship
            # ------------------------------------------------

            "option",

            # ------------------------------------------------
            # Value
            # ------------------------------------------------

            "name",
            "slug",
            "sort_order",

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            "is_active",

            # ------------------------------------------------
            # Related Product
            # ------------------------------------------------

            "product_id",

            # ------------------------------------------------
            # Computed
            # ------------------------------------------------

            "is_available",

            # ------------------------------------------------
            # Timestamps
            # ------------------------------------------------

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            # Identity
            "id",

            # Related product
            "product_id",

            # Computed
            "is_available",

            # Timestamps
            "created_at",
            "updated_at",
        ]





class ProductOptionValueCreateSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for creating a ProductOptionValue.

    The option should normally be assigned by the service/view.
    """

    class Meta:
        model = ProductOptionValue

        fields = [
            "id",
            "option",
            "name",
            "slug",
            "sort_order",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "option",
        ]




class ProductOptionValueUpdateSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for updating a ProductOptionValue.

    The option relationship cannot be changed through this
    serializer.
    """

    class Meta:
        model = ProductOptionValue

        fields = [
            "id",
            "option",
            "name",
            "slug",
            "sort_order",
            "is_active",
        ]

        read_only_fields = [
            "id",
            "option",
        ]