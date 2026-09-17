from rest_framework import serializers

from vendors.models import ProductVariantImage


# ============================================================
# Product Variant Image Serializer
# ============================================================

class ProductVariantImageSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for displaying a ProductVariantImage.

    Variant ownership is read-only.

    Image lifecycle operations such as:

        - create
        - update
        - delete
        - make primary
        - ensure primary

    should be handled by ProductVariantImageService.
    """

    # ========================================================
    # Related IDs
    # ========================================================

    variant_id = serializers.ReadOnlyField(
        source="variant_id",
    )

    product_id = serializers.ReadOnlyField(
        source="product_id",
    )

    # ========================================================
    # Meta
    # ========================================================

    class Meta:
        model = ProductVariantImage

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",

            # ------------------------------------------------
            # Relationships
            # ------------------------------------------------

            "variant",
            "variant_id",
            "product_id",

            # ------------------------------------------------
            # Image
            # ------------------------------------------------

            "image",
            "alt_text",

            # ------------------------------------------------
            # Display
            # ------------------------------------------------

            "is_primary",
            "display_order",

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            "is_active",
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

            # Relationships
            "variant",
            "variant_id",
            "product_id",

            # Computed
            "is_available",

            # Timestamps
            "created_at",
            "updated_at",
        ]





class ProductVariantImageCreateSerializer(
    serializers.ModelSerializer,
):
    class Meta:
        model = ProductVariantImage

        fields = [
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
        ]

        extra_kwargs = {
            "is_primary": {
                "required": False,
            },
            "display_order": {
                "required": False,
            },
            "is_active": {
                "required": False,
            },
        }