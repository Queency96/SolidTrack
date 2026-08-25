from rest_framework import serializers

from vendors.models import ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product-level images.

    Cloudinary handles the actual image storage.
    The API exposes the resulting image URL.
    """

    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage

        fields = [
            "id",
            "product",
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
        Return the absolute image URL.
        """

        if not obj.image:
            return None

        request = self.context.get("request")

        url = obj.image.url

        if request:
            return request.build_absolute_uri(url)

        return url