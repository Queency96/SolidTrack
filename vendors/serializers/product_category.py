from rest_framework import serializers
from vendors.models import ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for product categories.

    Used by the marketplace to display the global
    product category hierarchy.
    """

    is_root = serializers.ReadOnlyField()
    is_subcategory = serializers.ReadOnlyField()
    has_children = serializers.ReadOnlyField()
    product_count = serializers.ReadOnlyField()
    active_product_count = serializers.ReadOnlyField()

    class Meta:
        model = ProductCategory

        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "description",
            "image",
            "sort_order",
            "is_active",
            "is_root",
            "is_subcategory",
            "has_children",
            "product_count",
            "active_product_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "is_root",
            "is_subcategory",
            "has_children",
            "product_count",
            "active_product_count",
            "created_at",
            "updated_at",
        ]



class PublicProductCategorySerializer(
    serializers.ModelSerializer,
):
    """
    Serializer used by customers browsing
    the marketplace.
    """

    is_root = serializers.ReadOnlyField()
    is_subcategory = serializers.ReadOnlyField()
    has_children = serializers.ReadOnlyField()

    product_count = serializers.ReadOnlyField()
    active_product_count = serializers.ReadOnlyField()

    root_category_id = serializers.SerializerMethodField()

    class Meta:

        model = ProductCategory

        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "description",
            "image",
            "sort_order",
            "is_root",
            "is_subcategory",
            "has_children",
            "product_count",
            "active_product_count",
            "root_category_id",
        ]

        read_only_fields = fields

    def get_root_category_id(self, obj):

        root = obj.root_category

        return root.id if root else None