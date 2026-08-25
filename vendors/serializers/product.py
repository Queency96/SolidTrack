from rest_framework import serializers
from vendors.models.product import Product
from vendors.serializers.product_variant import (
    ProductVariantSerializer,
)
from vendors.models.product_variant import ProductVariant


class ProductSerializer(
    serializers.ModelSerializer
):
    variants = ProductVariantSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Product

        fields = [
            "id",
            "vendor",
            "category",
            "name",
            "slug",
            "description",
            "brand",
            "base_price",
            "sku",
            "is_active",
            "variants",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "variants",
            "created_at",
            "updated_at",
        ]



class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    vendor_name = serializers.CharField(
        source="vendor.business_name",
        read_only=True,
    )

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "slug",
            "brand",
            "category",
            "category_name",
            "vendor",
            "vendor_name",
            "base_price",
            "sku",
            "is_active",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "category_name",
            "vendor_name",
            "created_at",
        ]



class ProductDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    vendor_name = serializers.CharField(
        source="vendor.business_name",
        read_only=True,
    )

    variants = ProductVariantSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Product

        fields = [
            "id",
            "vendor",
            "vendor_name",
            "category",
            "category_name",
            "name",
            "slug",
            "description",
            "brand",
            "base_price",
            "sku",
            "is_active",
            "variants",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "vendor_name",
            "category_name",
            "variants",
            "created_at",
            "updated_at",
        ]

  


class ProductDetailVariantSerializer(
    serializers.ModelSerializer
):
    options = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant

        fields = [
            "id",
            "name",
            "sku",
            "price",
            "compare_at_price",
            "stock_quantity",
            "is_active",
            "options",
        ]

    def get_options(self, obj):
        return [
            {
                "option": item.option_value.option.name,
                "value": item.option_value.value,
            }
            for item in obj.option_values.select_related(
                "option_value__option"
            ).all()
        ]


class ProductDetailsSerializer(
    serializers.ModelSerializer
):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    variants = ProductDetailVariantSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Product

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "brand",
            "category",
            "category_name",
            "base_price",
            "sku",
            "variants",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields




class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Serializer used when creating a new product.

    The vendor is assigned by the view from the
    authenticated vendor account and must not be supplied
    by the client.
    """

    class Meta:
        model = Product

        fields = [
            "id",
            "category",
            "name",
            "description",
            "brand",
            "base_price",
            "sku",
            "is_active",
        ]

        read_only_fields = [
            "id",
        ]

    def validate_sku(self, value):
        """
        Prevent duplicate SKU values.
        """

        if Product.objects.filter(
            sku=value
        ).exists():
            raise serializers.ValidationError(
                "A product with this SKU already exists."
            )

        return value




class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer used when updating an existing product.

    Vendor ownership cannot be changed through this serializer.
    """

    class Meta:
        model = Product

        fields = [
            "id",
            "category",
            "name",
            "description",
            "brand",
            "base_price",
            "sku",
            "is_active",
        ]

        read_only_fields = [
            "id",
        ]

    def validate_sku(self, value):
        """
        Prevent the product from taking another product's SKU.
        """

        queryset = Product.objects.filter(
            sku=value
        ).exclude(
            pk=self.instance.pk
        )

        if queryset.exists():
            raise serializers.ValidationError(
                "A product with this SKU already exists."
            )

        return value