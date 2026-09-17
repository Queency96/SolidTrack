from rest_framework import serializers

from vendors.models import ProductImage


# ============================================================
# Product Image Serializer
# ============================================================

class ProductImageSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for ProductImage representation.

    Product ownership is controlled by the view/service and is
    therefore not writable through this serializer.

    Image lifecycle operations such as:

        - create
        - update
        - delete
        - make primary
        - ensure primary

    should be handled by ProductImageService.
    """

    # ========================================================
    # Related Product
    # ========================================================

    product_id = serializers.ReadOnlyField(
        source="product_id",
    )

    # ========================================================
    # Cloudinary URL
    # ========================================================

    image_url = serializers.SerializerMethodField()

    # ========================================================
    # Meta
    # ========================================================

    class Meta:
        model = ProductImage

        fields = [
            # ------------------------------------------------
            # Identity
            # ------------------------------------------------

            "id",

            # ------------------------------------------------
            # Relationship
            # ------------------------------------------------

            "product_id",

            # ------------------------------------------------
            # Image
            # ------------------------------------------------

            "image",
            "image_url",
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

            # ------------------------------------------------
            # Timestamps
            # ------------------------------------------------

            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            # Identity
            "id",

            # Relationship
            "product_id",

            # Computed
            "image_url",

            # Timestamps
            "created_at",
            "updated_at",
        ]

    # ========================================================
    # Cloudinary URL
    # ========================================================

    def get_image_url(self, obj):
        """
        Return the Cloudinary URL for the image.

        CloudinaryField normally exposes `.url`, but the
        fallback makes the serializer safe if the field contains
        an object without a usable URL property.
        """

        image = getattr(
            obj,
            "image",
            None,
        )

        if not image:
            return None

        try:
            url = image.url

            if url:
                return str(url)

        except (
            AttributeError,
            ValueError,
        ):
            pass

        try:
            value = str(image)

        except (AttributeError, ValueError):
            return None

        return value or None





class ProductImageCreateSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for creating a ProductImage.

    The product is assigned by the view/service.
    """

    class Meta:
        model = ProductImage

        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
        ]

        read_only_fields = [
            "id",
        ]




class ProductImageUpdateSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for updating an existing ProductImage.

    Product ownership cannot be changed.
    """

    class Meta:
        model = ProductImage

        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
        ]

        read_only_fields = [
            "id",
        ]