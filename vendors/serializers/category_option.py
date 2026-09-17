from rest_framework import serializers

from vendors.models import CategoryOption


class CategoryOptionSerializer(serializers.ModelSerializer):
    """
    Full serializer for CategoryOption.

    Used by vendor/admin APIs when viewing category options
    and when assigning category options to products.

    Category ownership should be controlled by the view/service;
    the serializer should not allow clients to move an existing
    CategoryOption to another category.
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
            "category_name",
            "is_inherited",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        """
        Prevent blank/whitespace-only option names.
        """
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Category option name cannot be empty."
            )

        return value


class CategoryOptionSimpleSerializer(serializers.ModelSerializer):
    """
    Lightweight read-only serializer for category options.

    Suitable for:
    - dropdowns
    - product creation forms
    - category option selectors
    - public category option listings
    """

    class Meta:
        model = CategoryOption

        fields = [
            "id",
            "name",
            "slug",
            "sort_order",
        ]

        read_only_fields = fields


class CategoryOptionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a CategoryOption.

    The category should normally be supplied by the URL/view/service,
    rather than trusted from the request body.
    """

    class Meta:
        model = CategoryOption

        fields = [
            "id",
            "name",
            "sort_order",
            "is_active",
        ]

        read_only_fields = [
            "id",
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Category option name cannot be empty."
            )

        return value


class CategoryOptionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating an existing CategoryOption.

    Category and inherited status cannot be changed here.
    """

    class Meta:
        model = CategoryOption

        fields = [
            "id",
            "name",
            "sort_order",
            "is_active",
        ]

        read_only_fields = [
            "id",
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Category option name cannot be empty."
            )

        return value


