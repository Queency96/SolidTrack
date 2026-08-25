from rest_framework import serializers
from vendors.models.product_variant_image import ProductVariantImage


class ProductVariantImageSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for images belonging to a specific
    product variant.

    Cloudinary handles image storage.
    """

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariantImage

        fields = [
            "id",
            "variant",
            "image",
            "image_url",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "image_url",
            "created_at",
            "updated_at",
        ]

    def get_image_url(self, obj):
        """
        Return the absolute Cloudinary image URL.
        """

        if not obj.image:
            return None

        request = self.context.get("request")

        url = obj.image.url

        if request:
            return request.build_absolute_uri(url)

        return url