from rest_framework import serializers
from vendors.models import CategoryOption


class CategoryOptionSerializer(serializers.ModelSerializer):
    """
    Serializer for category options.

    Used to display the available options for a category
    when creating or editing products.
    """

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    class Meta:

        model = CategoryOption

        fields = [
            "id",
            "name",
            "slug",
            "category",
            "category_name",
            "sort_order",
            "is_active",
            "is_inherited",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "is_inherited",
            "created_at",
            "updated_at",
        ]


class CategoryOptionSimpleSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for category options.
    
    Used for lightweight responses (e.g., dropdown lists).
    """

    class Meta:

        model = CategoryOption

        fields = [
            "id",
            "name",
            "slug",
            "sort_order",
        ]