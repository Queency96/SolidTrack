from rest_framework import serializers

from vendors.models import ProductVariant
from vendors.models.product import Product
from vendors.serializers.product_image import ProductImageSerializer
from vendors.serializers.product_variant import ProductVariantSerializer


class ProductSerializer(serializers.ModelSerializer):
    """Base product representation with the current model fields."""

    variants = ProductVariantSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "vendor",
            "store",
            "category",
            "name",
            "slug",
            "sku",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "stock_quantity",
            "track_inventory",
            "is_active",
            "is_published",
            "is_featured",
            "sort_order",
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
        source="vendor.company_name",
        read_only=True,
    )
    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )
    is_available = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "vendor",
            "vendor_name",
            "store",
            "store_name",
            "category",
            "category_name",
            "name",
            "slug",
            "sku",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "stock_quantity",
            "track_inventory",
            "is_active",
            "is_published",
            "is_featured",
            "sort_order",
            "is_available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "category_name",
            "vendor_name",
            "store_name",
            "is_available",
            "created_at",
            "updated_at",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )
    vendor_name = serializers.CharField(
        source="vendor.company_name",
        read_only=True,
    )
    store_name = serializers.CharField(
        source="store.name",
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
            "store",
            "store_name",
            "category",
            "category_name",
            "name",
            "slug",
            "sku",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "stock_quantity",
            "track_inventory",
            "is_active",
            "is_published",
            "is_featured",
            "sort_order",
            "is_available",
            "variants",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "vendor_name",
            "store_name",
            "category_name",
            "is_available",
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
            "price",
            "compare_at_price",
            "stock_quantity",
            "category",
            "category_name",
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
            "store",
            "category",
            "name",
            "sku",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "stock_quantity",
            "track_inventory",
            "is_active",
            "is_published",
            "is_featured",
            "sort_order",
        ]

        read_only_fields = [
            "id",
            "slug",
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
            "store",
            "category",
            "name",
            "sku",
            "short_description",
            "description",
            "price",
            "compare_at_price",
            "stock_quantity",
            "track_inventory",
            "is_active",
            "is_published",
            "is_featured",
            "sort_order",
        ]

        read_only_fields = [
            "id",
            "slug",
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


class PublicProductSerializer(
    serializers.ModelSerializer,
):
    """
    Lean product representation used by the public
    storefront when listing products.

    Only buyer-facing fields are exposed; internal
    vendor/store configuration is kept hidden.
    """

    category_name = serializers.CharField(
        source="category.name",
        read_only=True,
    )

    category_slug = serializers.CharField(
        source="category.slug",
        read_only=True,
    )

    vendor_name = serializers.CharField(
        source="vendor.company_name",
        read_only=True,
    )

    store_name = serializers.CharField(
        source="store.name",
        read_only=True,
    )

    store_slug = serializers.CharField(
        source="store.slug",
        read_only=True,
    )

    primary_image = serializers.SerializerMethodField()

    is_in_stock = serializers.ReadOnlyField()

    is_available = serializers.ReadOnlyField()

    class Meta:
        model = Product

        fields = [
            # Identity
            "id",
            "name",
            "slug",
            "sku",

            # Description
            "short_description",
            "description",

            # Pricing
            "price",
            "compare_at_price",

            # Category
            "category",
            "category_name",
            "category_slug",

            # Vendor
            "vendor",
            "vendor_name",

            # Store
            "store",
            "store_name",
            "store_slug",

            # Media
            "primary_image",

            # Status
            "is_featured",
            "is_in_stock",
            "is_available",

            # Timestamps
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields

    def get_primary_image(self, obj):
        """
        Return the URL of the first usable image.

        Prefers the flagged primary image, otherwise
        the first active image in display order.
        """

        images = list(obj.images.all())

        if not images:
            return None

        image = next(
            (
                item
                for item in images
                if (
                    item.is_active
                    and item.is_primary
                )
            ),
            None,
        )

        if image is None:
            image = next(
                (
                    item
                    for item in images
                    if item.is_active
                ),
                None,
            )

        if image is None or not image.image:
            return None

        request = self.context.get("request")

        url = image.image.url

        if request:
            return request.build_absolute_uri(url)

        return url


class PublicProductDetailSerializer(
    PublicProductSerializer,
):
    """
    Full product representation shown when a customer
    opens a single product on the storefront.
    """

    images = ProductImageSerializer(
        many=True,
        read_only=True,
    )

    variants = ProductVariantSerializer(
        many=True,
        read_only=True,
    )

    class Meta(PublicProductSerializer.Meta):

        fields = (
            PublicProductSerializer.Meta.fields
            + [
                "images",
                "variants",
            ]
        )

        read_only_fields = fields