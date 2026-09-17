from rest_framework import serializers

from vendors.models.product import Product
from vendors.serializers.product_image import ProductImageSerializer
from vendors.serializers.product_variant import ProductVariantSerializer
from vendors.serializers.product_option import ProductOptionSerializer
from vendors.serializers.category_option import CategoryOptionSimpleSerializer


from django.db import transaction
from rest_framework import serializers

from vendors.models import (
    Product,
    ProductImage,
    ProductCategory,
    CategoryOption,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    ProductVariantImage,
    ProductVariantOptionValue,
)



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













class ProductImageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an image belonging to a product.
    """

    class Meta:
        model = ProductImage
        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
        ]
        read_only_fields = ["id"]


class ProductVariantImageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an image belonging to a product variant.
    """

    class Meta:
        model = ProductVariantImage
        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
        ]
        read_only_fields = ["id"]


class ProductOptionValueCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a value belonging to a product option.

    Example:
        Color
            - Black
            - White
            - Blue
    """

    class Meta:
        model = ProductOptionValue
        fields = [
            "id",
            "name",
            "value",
            "sort_order",
            "is_active",
        ]
        read_only_fields = ["id"]


class ProductOptionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a product option and its values.

    Example:
        {
            "name": "Color",
            "sort_order": 0,
            "values": [
                {
                    "name": "Black",
                    "value": "black"
                },
                {
                    "name": "White",
                    "value": "white"
                }
            ]
        }
    """

    values = ProductOptionValueCreateSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = ProductOption
        fields = [
            "id",
            "name",
            "sort_order",
            "values",
        ]
        read_only_fields = ["id"]


class ProductVariantOptionValueCreateSerializer(
    serializers.Serializer
):
    """
    Identifies which ProductOptionValue records belong to a variant.

    The client submits ProductOptionValue IDs.

    Example:
        {
            "option_value_ids": [12, 17]
        }
    """

    option_value_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )


class ProductVariantCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a product variant.

    A variant references existing ProductOptionValue records belonging
    to the same product.

    Example:

        {
            "name": "Black / 128GB",
            "sku": "IPH15-BLK-128",
            "price": "950000.00",
            "stock_quantity": 10,
            "option_value_ids": [
                "uuid-of-black",
                "uuid-of-128gb"
            ],
            "images": [
                {
                    "image": "...",
                    "is_primary": true,
                    "display_order": 0
                }
            ]
        }
    """

    option_value_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        write_only=True,
    )

    images = ProductVariantImageCreateSerializer(
        many=True,
        required=False,
    )

    class Meta:
        model = ProductVariant
        fields = [
            "id",
            "name",
            "sku",
            "price",
            "compare_at_price",
            "stock_quantity",
            "track_inventory",
            "weight",
            "is_active",
            "is_default",
            "sort_order",
            "option_value_ids",
            "images",
        ]
        read_only_fields = ["id"]

    def validate_option_value_ids(self, value):
        """
        Prevent the same option value from being selected twice.
        """
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate option values are not allowed."
            )

        return value







#----------------------------------
# EXAMPLE PRODUCT CREATION PAYLOAD
#----------------------------------

# {
#   "vendor": "VENDOR_UUID",
#   "store": "STORE_UUID",
#   "category": "CATEGORY_UUID",
#   "name": "iPhone 15",
#   "short_description": "Latest Apple smartphone",
#   "description": "Detailed product description",
#   "price": "950000.00",
#   "compare_at_price": "1050000.00",
#   "stock_quantity": 20,
#   "track_inventory": true,
#   "is_active": true,
#   "is_published": true,
#   "is_featured": false,
#   "sort_order": 0,

#   "images": [
#     {
#       "image": "PRODUCT_IMAGE_FILE",
#       "alt_text": "iPhone 15",
#       "is_primary": true,
#       "display_order": 0
#     },
#     {
#       "image": "SECOND_PRODUCT_IMAGE_FILE",
#       "alt_text": "iPhone 15 rear",
#       "is_primary": false,
#       "display_order": 1
#     }
#   ],

#   "options": [
#     {
#       "name": "Color",
#       "sort_order": 0,
#       "is_required": true,
#       "values": [
#         {
#           "name": "Black",
#           "value": "black",
#           "sort_order": 0,
#           "is_active": true
#         },
#         {
#           "name": "White",
#           "value": "white",
#           "sort_order": 1,
#           "is_active": true
#         },
#         {
#           "name": "Blue",
#           "value": "blue",
#           "sort_order": 2,
#           "is_active": true
#         }
#       ]
#     },
#     {
#       "name": "Storage",
#       "sort_order": 1,
#       "is_required": true,
#       "values": [
#         {
#           "name": "128GB",
#           "value": "128gb",
#           "sort_order": 0,
#           "is_active": true
#         },
#         {
#           "name": "256GB",
#           "value": "256gb",
#           "sort_order": 1,
#           "is_active": true
#         }
#       ]
#     }
#   ],

#   "variants": [
#     {
#       "name": "Black / 128GB",
#       "sku": "IPH15-BLK-128",
#       "price": "950000.00",
#       "compare_at_price": "1050000.00",
#       "stock_quantity": 10,
#       "track_inventory": true,
#       "weight": "0.171",
#       "is_active": true,
#       "is_default": true,
#       "sort_order": 0,

#       "option_value_ids": [
#         "BLACK_OPTION_VALUE_UUID",
#         "128GB_OPTION_VALUE_UUID"
#       ],

#       "images": [
#         {
#           "image": "BLACK_FRONT_IMAGE_FILE",
#           "alt_text": "iPhone 15 Black front",
#           "is_primary": true,
#           "display_order": 0,
#           "is_active": true
#         },
#         {
#           "image": "BLACK_BACK_IMAGE_FILE",
#           "alt_text": "iPhone 15 Black back",
#           "is_primary": false,
#           "display_order": 1,
#           "is_active": true
#         }
#       ]
#     },

#     {
#       "name": "White / 128GB",
#       "sku": "IPH15-WHT-128",
#       "price": "950000.00",
#       "compare_at_price": "1050000.00",
#       "stock_quantity": 8,
#       "track_inventory": true,
#       "weight": "0.171",
#       "is_active": true,
#       "is_default": false,
#       "sort_order": 1,

#       "option_value_ids": [
#         "WHITE_OPTION_VALUE_UUID",
#         "128GB_OPTION_VALUE_UUID"
#       ],

#       "images": [
#         {
#           "image": "WHITE_FRONT_IMAGE_FILE",
#           "alt_text": "iPhone 15 White front",
#           "is_primary": true,
#           "display_order": 0,
#           "is_active": true
#         },
#         {
#           "image": "WHITE_BACK_IMAGE_FILE",
#           "alt_text": "iPhone 15 White back",
#           "is_primary": false,
#           "display_order": 1,
#           "is_active": true
#         }
#       ]
#     }
#   ]
# }





from django.db import transaction
from django.utils.text import slugify

from rest_framework import serializers

from vendors.models import (
    Product,
    ProductCategory,
    CategoryOption,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    ProductVariantOptionValue,
    ProductImage,
    ProductVariantImage,
    VendorStore,
)


# ============================================================
# CATEGORY OPTION
# ============================================================

class CategoryOptionSerializer(serializers.ModelSerializer):
    """
    Read-only representation of options configured for a category.

    Example:

    {
        "id": "...",
        "name": "Colour",
        "slug": "colour",
        "sort_order": 0
    }
    """

    class Meta:
        model = CategoryOption
        fields = [
            "id",
            "name",
            "slug",
            "sort_order",
            "is_active",
        ]
        read_only_fields = fields


# ============================================================
# PRODUCT OPTION VALUE
# ============================================================

class ProductOptionValueSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProductOptionValue
        fields = [
            "id",
            "name",
            "slug",
            "sort_order",
            "is_active",
        ]
        read_only_fields = fields


# ============================================================
# PRODUCT OPTION
# ============================================================

class ProductOptionSerializer(
    serializers.ModelSerializer
):
    values = ProductOptionValueSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ProductOption
        fields = [
            "id",
            "name",
            "slug",
            "sort_order",
            "is_active",
            "values",
        ]
        read_only_fields = fields


# ============================================================
# PRODUCT IMAGE
# ============================================================

class ProductImageSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProductImage

        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                "An image is required."
            )

        return value


# ============================================================
# VARIANT IMAGE
# ============================================================

class ProductVariantImageSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProductVariantImage

        fields = [
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                "An image is required."
            )

        return value


# ============================================================
# PRODUCT OPTION INPUT
# ============================================================

class ProductOptionInputSerializer(
    serializers.Serializer
):
    """
    Vendor selects an option defined by the category and supplies
    the values that this product supports.

    Example:

    {
        "category_option": "uuid",
        "values": [
            "Black",
            "White",
            "Blue"
        ]
    }
    """

    category_option = serializers.PrimaryKeyRelatedField(
        queryset=CategoryOption.objects.filter(
            is_active=True
        )
    )

    values = serializers.ListField(
        child=serializers.CharField(
            max_length=100,
            trim_whitespace=True,
            allow_blank=False,
        ),
        allow_empty=False,
    )

    def validate_values(self, values):
        cleaned = []
        seen = set()

        for value in values:
            value = value.strip()

            if not value:
                raise serializers.ValidationError(
                    "Option values cannot be empty."
                )

            normalized = value.casefold()

            if normalized in seen:
                raise serializers.ValidationError(
                    f"Duplicate option value '{value}'."
                )

            seen.add(normalized)
            cleaned.append(value)

        return cleaned


# ============================================================
# VARIANT INPUT
# ============================================================

class ProductVariantInputSerializer(
    serializers.Serializer
):
    """
    Variant input.

    option_values contains the values by category option ID.

    Example:

    {
        "name": "Black / 128GB",
        "sku": "IPH15-BLK-128",
        "option_values": {
            "colour-category-option-uuid": "Black",
            "storage-category-option-uuid": "128GB"
        },
        "price": "950000.00",
        "compare_at_price": "1000000.00",
        "stock_quantity": 10,
        "track_inventory": true,
        "weight": "0.171",
        "is_active": true,
        "is_default": false,
        "is_available": true,
        "sort_order": 0
    }
    """

    name = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )

    sku = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
        trim_whitespace=True,
    )

    option_values = serializers.DictField(
        child=serializers.CharField(
            max_length=100,
            trim_whitespace=True,
            allow_blank=False,
        ),
        required=False,
        default=dict,
    )

    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )

    compare_at_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
    )

    stock_quantity = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )

    track_inventory = serializers.BooleanField(
        required=False,
        default=True,
    )

    weight = serializers.DecimalField(
        max_digits=10,
        decimal_places=3,
        required=False,
        allow_null=True,
        min_value=0,
    )

    is_active = serializers.BooleanField(
        required=False,
        default=True,
    )

    is_default = serializers.BooleanField(
        required=False,
        default=False,
    )

    is_available = serializers.BooleanField(
        required=False,
        default=True,
    )

    sort_order = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Variant name cannot be empty."
            )

        return value

    def validate_option_values(self, value):
        cleaned = {}

        for option_id, option_value in value.items():
            option_value = option_value.strip()

            if not option_value:
                raise serializers.ValidationError(
                    "Variant option values cannot be empty."
                )

            cleaned[str(option_id)] = option_value

        return cleaned

    def validate(self, attrs):
        price = attrs.get("price")
        compare_at_price = attrs.get(
            "compare_at_price"
        )

        if (
            compare_at_price is not None
            and price is not None
            and compare_at_price < price
        ):
            raise serializers.ValidationError({
                "compare_at_price": (
                    "Compare-at price cannot be lower "
                    "than the variant price."
                )
            })

        return attrs


# ============================================================
# PRODUCT CREATE SERIALIZER
# ============================================================

class ProductCreateSerializer(
    serializers.ModelSerializer
):
    """
    Creates a product together with its product options,
    option values and variants.

    The vendor is NEVER accepted from the request.

    The authenticated vendor is automatically assigned.
    """

    options = ProductOptionInputSerializer(
        many=True,
        required=False,
        default=list,
    )

    variants = ProductVariantInputSerializer(
        many=True,
        required=False,
        default=list,
    )

    class Meta:
        model = Product

        fields = [
            "id",
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
            "options",
            "variants",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "updated_at",
        ]

    # ========================================================
    # VENDOR
    # ========================================================

    def _get_vendor(self):
        request = self.context.get("request")

        if request is None:
            raise serializers.ValidationError(
                "Request context is required."
            )

        user = request.user

        if not user or not user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        # Your VendorProfile is expected to be related to User.
        #
        # If your actual reverse relation is different,
        # change ONLY this lookup.
        try:
            return user.vendor_profile
        except AttributeError:
            pass

        from vendors.models import VendorProfile

        vendor = VendorProfile.objects.filter(
            user=user
        ).first()

        if vendor is None:
            raise serializers.ValidationError(
                "The authenticated user does not have a vendor profile."
            )

        return vendor

    # ========================================================
    # CATEGORY
    # ========================================================

    def _validate_category(
        self,
        category,
        vendor,
    ):
        if category is None:
            raise serializers.ValidationError({
                "category": "Category is required."
            })

        category_vendor_id = getattr(
            category,
            "vendor_id",
            None,
        )

        if (
            category_vendor_id is not None
            and category_vendor_id != vendor.id
        ):
            raise serializers.ValidationError({
                "category": (
                    "The selected category does not "
                    "belong to this vendor."
                )
            })

    # ========================================================
    # STORE
    # ========================================================

    def _validate_store(
        self,
        store,
        vendor,
    ):
        if store is None:
            raise serializers.ValidationError({
                "store": "Store is required."
            })

        if store.vendor_id != vendor.id:
            raise serializers.ValidationError({
                "store": (
                    "The selected store does not "
                    "belong to this vendor."
                )
            })

    # ========================================================
    # OPTIONS
    # ========================================================

    def _validate_options(
        self,
        category,
        options,
    ):
        """
        Verify that every requested ProductOption comes from
        the selected ProductCategory.
        """

        category_options = {
            str(option.id): option
            for option in CategoryOption.objects.filter(
                category=category,
                is_active=True,
            )
        }

        seen = set()

        for option_data in options:
            category_option = (
                option_data["category_option"]
            )

            option_id = str(
                category_option.id
            )

            if option_id in seen:
                raise serializers.ValidationError({
                    "options": (
                        f"Duplicate category option "
                        f"'{category_option.name}'."
                    )
                })

            seen.add(option_id)

            if option_id not in category_options:
                raise serializers.ValidationError({
                    "options": (
                        f"'{category_option.name}' is not "
                        "defined for the selected category."
                    )
                })

        return category_options

    # ========================================================
    # VARIANTS
    # ========================================================

    def _validate_variants(
        self,
        options,
        variants,
    ):
        if not variants:
            return

        # ----------------------------------------------
        # Build:
        #
        # category_option_id -> allowed value names
        # ----------------------------------------------

        option_map = {}

        for option_data in options:
            category_option = (
                option_data["category_option"]
            )

            option_id = str(
                category_option.id
            )

            option_map[option_id] = {
                value.casefold(): value
                for value in option_data["values"]
            }

        default_count = 0
        combinations = set()

        for index, variant in enumerate(variants):
            if variant.get(
                "is_default",
                False,
            ):
                default_count += 1

            variant_options = variant.get(
                "option_values",
                {},
            )

            # ------------------------------------------
            # Product has options, therefore each variant
            # must provide exactly one value for every
            # configured option.
            # ------------------------------------------

            if option_map:
                expected_options = set(
                    option_map.keys()
                )

                provided_options = set(
                    str(key)
                    for key in variant_options.keys()
                )

                missing = (
                    expected_options
                    - provided_options
                )

                extra = (
                    provided_options
                    - expected_options
                )

                if missing:
                    raise serializers.ValidationError({
                        "variants": {
                            index: {
                                "option_values": (
                                    "The variant is missing "
                                    "values for one or more "
                                    "product options."
                                ),
                                "missing_options": list(
                                    missing
                                ),
                            }
                        }
                    })

                if extra:
                    raise serializers.ValidationError({
                        "variants": {
                            index: {
                                "option_values": (
                                    "The variant contains "
                                    "an option that is not "
                                    "configured for this product."
                                ),
                                "unknown_options": list(
                                    extra
                                ),
                            }
                        }
                    })

            # ------------------------------------------
            # Validate every value.
            # ------------------------------------------

            resolved_combination = []

            for option_id, value_name in (
                variant_options.items()
            ):
                option_id = str(option_id)

                if option_id not in option_map:
                    raise serializers.ValidationError({
                        "variants": {
                            index: {
                                "option_values": (
                                    f"Category option "
                                    f"'{option_id}' is not "
                                    "configured for this product."
                                )
                            }
                        }
                    })

                normalized_value = (
                    value_name.casefold()
                )

                if normalized_value not in option_map[
                    option_id
                ]:
                    raise serializers.ValidationError({
                        "variants": {
                            index: {
                                "option_values": (
                                    f"'{value_name}' is not "
                                    f"a value configured for "
                                    f"category option "
                                    f"'{option_id}'."
                                )
                            }
                        }
                    })

                resolved_combination.append(
                    (
                        option_id,
                        normalized_value,
                    )
                )

            # ------------------------------------------
            # Detect duplicate combinations.
            # ------------------------------------------

            combination_key = tuple(
                sorted(resolved_combination)
            )

            if combination_key in combinations:
                raise serializers.ValidationError({
                    "variants": {
                        index: {
                            "option_values": (
                                "This variant combination "
                                "already exists."
                            )
                        }
                    }
                })

            combinations.add(
                combination_key
            )

        if default_count > 1:
            raise serializers.ValidationError({
                "variants": (
                    "Only one variant can be the "
                    "default variant."
                )
            })

    # ========================================================
    # VALIDATE
    # ========================================================

    def validate(self, attrs):
        vendor = self._get_vendor()

        category = attrs.get(
            "category"
        )

        store = attrs.get(
            "store"
        )

        options = attrs.get(
            "options",
            [],
        )

        variants = attrs.get(
            "variants",
            [],
        )

        self._validate_category(
            category,
            vendor,
        )

        self._validate_store(
            store,
            vendor,
        )

        self._validate_options(
            category,
            options,
        )

        self._validate_variants(
            options,
            variants,
        )

        # ----------------------------------------------
        # Product SKU
        # ----------------------------------------------

        sku = attrs.get(
            "sku",
            ""
        ).strip()

        if sku and Product.objects.filter(
            vendor=vendor,
            sku=sku,
        ).exists():
            raise serializers.ValidationError({
                "sku": (
                    "A product with this SKU already "
                    "exists for this vendor."
                )
            })

        # ----------------------------------------------
        # Product price
        # ----------------------------------------------

        price = attrs.get("price")

        if price is not None and price < 0:
            raise serializers.ValidationError({
                "price": (
                    "Product price cannot be negative."
                )
            })

        compare_at_price = attrs.get(
            "compare_at_price"
        )

        if (
            compare_at_price is not None
            and price is not None
            and compare_at_price < price
        ):
            raise serializers.ValidationError({
                "compare_at_price": (
                    "Compare-at price cannot be lower "
                    "than the selling price."
                )
            })

        return attrs

    # ========================================================
    # CREATE
    # ========================================================

    @transaction.atomic
    def create(self, validated_data):
        options_data = validated_data.pop(
            "options",
            [],
        )

        variants_data = validated_data.pop(
            "variants",
            [],
        )

        vendor = self._get_vendor()

        # Never trust vendor from client.
        validated_data["vendor"] = vendor

        # ----------------------------------------------
        # Generate unique vendor slug
        # ----------------------------------------------

        name = validated_data["name"].strip()

        base_slug = slugify(name)

        if not base_slug:
            base_slug = "product"

        slug = base_slug
        counter = 2

        while Product.objects.filter(
            vendor=vendor,
            slug=slug,
        ).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        validated_data["slug"] = slug

        # ----------------------------------------------
        # Create Product
        # ----------------------------------------------

        product = Product.objects.create(
            **validated_data
        )

        # ----------------------------------------------
        # Create ProductOptions and Values
        # ----------------------------------------------

        option_values_by_category_option = {}

        for option_data in options_data:
            category_option = (
                option_data["category_option"]
            )

            product_option = ProductOption.objects.create(
                product=product,
                name=category_option.name,
                slug=category_option.slug,
                sort_order=category_option.sort_order,
                is_active=True,
            )

            value_map = {}

            for index, value_name in enumerate(
                option_data["values"]
            ):
                product_value = (
                    ProductOptionValue.objects.create(
                        option=product_option,
                        name=value_name,
                        slug=slugify(value_name),
                        sort_order=index,
                        is_active=True,
                    )
                )

                value_map[
                    value_name.casefold()
                ] = product_value

            option_values_by_category_option[
                str(category_option.id)
            ] = {
                "option": product_option,
                "values": value_map,
            }

        # ----------------------------------------------
        # Create variants
        # ----------------------------------------------

        for variant_data in variants_data:
            variant_option_values = (
                variant_data.pop(
                    "option_values",
                    {},
                )
            )

            variant = ProductVariant.objects.create(
                product=product,
                **variant_data,
            )

            for (
                category_option_id,
                value_name,
            ) in variant_option_values.items():

                option_data = (
                    option_values_by_category_option.get(
                        str(category_option_id)
                    )
                )

                if option_data is None:
                    raise serializers.ValidationError({
                        "variants": (
                            f"Category option "
                            f"'{category_option_id}' "
                            "could not be resolved."
                        )
                    })

                product_value = (
                    option_data["values"].get(
                        value_name.casefold()
                    )
                )

                if product_value is None:
                    raise serializers.ValidationError({
                        "variants": (
                            f"Option value "
                            f"'{value_name}' could not "
                            "be resolved."
                        )
                    })

                ProductVariantOptionValue.objects.create(
                    variant=variant,
                    option_value=product_value,
                )

        return product


# ============================================================
# VARIANT OUTPUT
# ============================================================

class ProductVariantSerializer(
    serializers.ModelSerializer
):
    option_values = serializers.SerializerMethodField()
    images = ProductVariantImageSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ProductVariant

        fields = [
            "id",
            "name",
            "sku",
            "option_values",
            "price",
            "compare_at_price",
            "stock_quantity",
            "track_inventory",
            "weight",
            "is_active",
            "is_default",
            "is_available",
            "sort_order",
            "productvariantimage",
            "images",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def get_option_values(self, obj):
        values = (
            obj.option_values
            .select_related("option")
            .order_by(
                "option__sort_order",
                "sort_order",
                "name",
            )
        )

        return [
            {
                "id": str(value.id),
                "option": {
                    "id": str(value.option.id),
                    "name": value.option.name,
                    "slug": value.option.slug,
                },
                "name": value.name,
                "slug": value.slug,
            }
            for value in values
        ]


# ============================================================
# PRODUCT OUTPUT
# ============================================================

class ProductSerializer(
    serializers.ModelSerializer
):
    options = ProductOptionSerializer(
        many=True,
        read_only=True,
    )

    variants = ProductVariantSerializer(
        many=True,
        read_only=True,
    )

    images = ProductImageSerializer(
        many=True,
        read_only=True,
    )

    applicable_category_options = serializers.SerializerMethodField()

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
            "applicable_category_options",
            "options",
            "variants",
            "images",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "vendor",
            "slug",
            "applicable_category_options",
            "options",
            "variants",
            "images",
            "created_at",
            "updated_at",
        ]

    def get_applicable_category_options(self, obj):
        if not obj.category_id:
            return []

        queryset = (
            CategoryOption.objects
            .filter(
                category=obj.category,
                is_active=True,
            )
            .order_by(
                "sort_order",
                "name",
            )
        )

        return CategoryOptionSerializer(
            queryset,
            many=True,
        ).data