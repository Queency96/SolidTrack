from rest_framework import serializers
from vendors.models import ProductOptionValue


class ProductOptionValueSerializer(
    serializers.ModelSerializer,
):
    """
    Serializer for selectable product option values.

    Example:

        Color
            ├── Black
            ├── White
            └── Blue
    """

    product_id = serializers.ReadOnlyField()
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