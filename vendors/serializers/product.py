from django.db import transaction
from django.db.models import Prefetch
from django.utils.text import slugify

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
    VendorStore,
    VendorProfile,
)


# ============================================================
# CATEGORY OPTION
# ============================================================


class CategoryOptionSerializer(
    serializers.ModelSerializer
):
    """
    Read-only representation of a category option.
    """

    class Meta:
        model = CategoryOption

        fields = (
            "id",
            "name",
            "slug",
            "sort_order",
            "is_active",
        )

        read_only_fields = fields


# ============================================================
# PRODUCT OPTION VALUE
# ============================================================


class ProductOptionValueSerializer(
    serializers.ModelSerializer
):
    """
    Read-only representation of a product option value.
    """

    class Meta:
        model = ProductOptionValue

        fields = (
            "id",
            "name",
            "slug",
            "sort_order",
            "is_active",
        )

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

        fields = (
            "id",
            "name",
            "slug",
            "sort_order",
            "is_active",
            "values",
        )

        read_only_fields = fields


# ============================================================
# PRODUCT IMAGE
# ============================================================


class ProductImageSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProductImage

        fields = (
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                "An image is required."
            )

        return value


# ============================================================
# PRODUCT VARIANT IMAGE
# ============================================================


class ProductVariantImageSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProductVariantImage

        fields = (
            "id",
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
        )

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                "An image is required."
            )

        return value


# ============================================================
# CREATE IMAGE INPUT
# ============================================================


class ProductImageCreateSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProductImage

        fields = (
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
        )

        extra_kwargs = {
            "is_primary": {
                "required": False,
                "default": False,
            },
            "display_order": {
                "required": False,
                "default": 0,
            },
            "is_active": {
                "required": False,
                "default": True,
            },
            "alt_text": {
                "required": False,
                "allow_blank": True,
                "default": "",
            },
        }

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                "An image is required."
            )

        return value


class ProductVariantImageCreateSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = ProductVariantImage

        fields = (
            "image",
            "alt_text",
            "is_primary",
            "display_order",
            "is_active",
        )

        extra_kwargs = {
            "is_primary": {
                "required": False,
                "default": False,
            },
            "display_order": {
                "required": False,
                "default": 0,
            },
            "is_active": {
                "required": False,
                "default": True,
            },
            "alt_text": {
                "required": False,
                "allow_blank": True,
                "default": "",
            },
        }

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

    sort_order = serializers.IntegerField(
        min_value=0,
        required=False,
        default=0,
    )

    images = ProductVariantImageCreateSerializer(
        many=True,
        required=False,
        default=list,
    )

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Variant name cannot be empty."
            )

        return value

    # --------------------------------------------------------
    # SKU
    # --------------------------------------------------------

    def validate_sku(self, value):
        return value.strip()

    # --------------------------------------------------------
    # OPTION VALUES
    # --------------------------------------------------------

    def validate_option_values(self, value):
        cleaned = {}

        for option_id, option_value in value.items():
            option_value = option_value.strip()

            if not option_value:
                raise serializers.ValidationError(
                    "Variant option values cannot be empty."
                )

            option_id = str(option_id).strip()

            if not option_id:
                raise serializers.ValidationError(
                    "Variant option IDs cannot be empty."
                )

            cleaned[option_id] = option_value

        return cleaned

    # --------------------------------------------------------
    # IMAGES
    # --------------------------------------------------------

    def validate_images(self, images):
        primary_count = sum(
            1
            for image in images
            if image.get("is_primary", False)
        )

        if primary_count > 1:
            raise serializers.ValidationError(
                "Only one variant image can be primary."
            )

        return images

    # --------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------

    def validate(self, attrs):
        price = attrs.get("price")

        compare_at_price = attrs.get(
            "compare_at_price"
        )

        if (
            price is not None
            and compare_at_price is not None
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
# PRODUCT CREATE
# ============================================================


class ProductCreateSerializer(
    serializers.ModelSerializer
):
    """
    Creates:

        Product
            ├── ProductImage
            ├── ProductOption
            │      └── ProductOptionValue
            └── ProductVariant
                   ├── ProductVariantOptionValue
                   └── ProductVariantImage

    Vendor is always obtained from the authenticated user.
    """

    images = ProductImageCreateSerializer(
        many=True,
        required=False,
        default=list,
    )

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

        fields = (
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
            "images",
            "options",
            "variants",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "slug",
            "created_at",
            "updated_at",
        )

    # ========================================================
    # VENDOR
    # ========================================================

    def _get_vendor(self):
        vendor = self.context.get("_vendor")

        if vendor is not None:
            return vendor

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

        vendor = getattr(
            user,
            "vendor_profile",
            None,
        )

        if vendor is None:
            vendor = (
                VendorProfile.objects
                .filter(user=user)
                .first()
            )

        if vendor is None:
            raise serializers.ValidationError(
                "The authenticated user does not "
                "have a vendor profile."
            )

        self.context["_vendor"] = vendor

        return vendor

    # ========================================================
    # CATEGORY
    # ========================================================

    def _validate_category(self, category):
        """
        ProductCategory is global.

        It does NOT belong to a vendor.

        Therefore we only validate that a category was supplied
        and that it is active.
        """

        if category is None:
            raise serializers.ValidationError({
                "category": "Category is required."
            })

        if not category.is_active:
            raise serializers.ValidationError({
                "category": (
                    "The selected category is inactive."
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

        if not store.is_active:
            raise serializers.ValidationError({
                "store": (
                    "The selected store is inactive."
                )
            })

    # ========================================================
    # IMAGES
    # ========================================================

    def _validate_images(self, images):
        primary_count = sum(
            1
            for image in images
            if image.get("is_primary", False)
        )

        if primary_count > 1:
            raise serializers.ValidationError({
                "images": (
                    "Only one product image can "
                    "be primary."
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
        category_options = {
            str(option.id): option
            for option in (
                CategoryOption.objects
                .filter(
                    category_id=category.id,
                    is_active=True,
                )
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

        option_map = {
            str(
                option_data[
                    "category_option"
                ].id
            ): {
                value.casefold(): value
                for value in option_data["values"]
            }
            for option_data in options
        }

        expected_options = set(
            option_map.keys()
        )

        combinations = set()
        default_count = 0

        for index, variant in enumerate(
            variants
        ):
            if variant.get("is_default"):
                default_count += 1

            variant_options = variant.get(
                "option_values",
                {},
            )

            provided_options = {
                str(key)
                for key in variant_options.keys()
            }

            # ------------------------------------------------
            # No product options
            # ------------------------------------------------

            if not option_map:
                if provided_options:
                    raise serializers.ValidationError({
                        "variants": {
                            index: {
                                "option_values": (
                                    "This product has no configured "
                                    "options, so the variant cannot "
                                    "contain option values."
                                )
                            }
                        }
                    })

            # ------------------------------------------------
            # Product has options
            # ------------------------------------------------

            else:
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
                                    "one or more product options."
                                ),
                                "missing_options": sorted(
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
                                "unknown_options": sorted(
                                    extra
                                ),
                            }
                        }
                    })

            # ------------------------------------------------
            # Validate individual option values
            # ------------------------------------------------

            combination = []

            for (
                option_id,
                value_name,
            ) in variant_options.items():

                option_id = str(option_id)

                normalized_value = (
                    value_name.casefold()
                )

                if option_id not in option_map:
                    raise serializers.ValidationError({
                        "variants": {
                            index: {
                                "option_values": (
                                    f"Unknown category option "
                                    f"'{option_id}'."
                                )
                            }
                        }
                    })

                if (
                    normalized_value
                    not in option_map[option_id]
                ):
                    raise serializers.ValidationError({
                        "variants": {
                            index: {
                                "option_values": (
                                    f"'{value_name}' is not "
                                    "configured for the selected "
                                    f"option '{option_id}'."
                                )
                            }
                        }
                    })

                combination.append(
                    (
                        option_id,
                        normalized_value,
                    )
                )

            combination_key = tuple(
                sorted(combination)
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
                    "Only one variant can be "
                    "the default variant."
                )
            })

    # ========================================================
    # VALIDATE
    # ========================================================

    def validate(self, attrs):
        vendor = self._get_vendor()

        category = attrs.get("category")
        store = attrs.get("store")

        images = attrs.get(
            "images",
            [],
        )

        options = attrs.get(
            "options",
            [],
        )

        variants = attrs.get(
            "variants",
            [],
        )

        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------

        self._validate_category(
            category
        )

        # ----------------------------------------------------
        # Store
        # ----------------------------------------------------

        self._validate_store(
            store,
            vendor,
        )

        # ----------------------------------------------------
        # Images
        # ----------------------------------------------------

        self._validate_images(
            images
        )

        # ----------------------------------------------------
        # Options
        # ----------------------------------------------------

        self._validate_options(
            category,
            options,
        )

        # ----------------------------------------------------
        # Variants
        # ----------------------------------------------------

        self._validate_variants(
            options,
            variants,
        )

        # ----------------------------------------------------
        # Product SKU
        # ----------------------------------------------------

        sku = (
            attrs.get("sku") or ""
        ).strip()

        if sku and Product.objects.filter(
            vendor_id=vendor.id,
            sku=sku,
        ).exists():
            raise serializers.ValidationError({
                "sku": (
                    "A product with this SKU already "
                    "exists for this vendor."
                )
            })

        # ----------------------------------------------------
        # Product pricing
        # ----------------------------------------------------

        price = attrs.get("price")

        compare_at_price = attrs.get(
            "compare_at_price"
        )

        if (
            price is not None
            and price < 0
        ):
            raise serializers.ValidationError({
                "price": (
                    "Product price cannot be negative."
                )
            })

        if (
            compare_at_price is not None
            and compare_at_price < 0
        ):
            raise serializers.ValidationError({
                "compare_at_price": (
                    "Compare-at price cannot be negative."
                )
            })

        if (
            price is not None
            and compare_at_price is not None
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
    # SLUG
    # ========================================================

    def _generate_unique_slug(
        self,
        *,
        vendor,
        name,
    ):
        base_slug = (
            slugify(name)
            or "product"
        )

        slug = base_slug

        if not Product.objects.filter(
            vendor_id=vendor.id,
            slug=slug,
        ).exists():
            return slug

        counter = 2

        while Product.objects.filter(
            vendor_id=vendor.id,
            slug=f"{base_slug}-{counter}",
        ).exists():
            counter += 1

        return f"{base_slug}-{counter}"

    # ========================================================
    # CREATE
    # ========================================================

    @transaction.atomic
    def create(self, validated_data):
        images_data = validated_data.pop(
            "images",
            [],
        )

        options_data = validated_data.pop(
            "options",
            [],
        )

        variants_data = validated_data.pop(
            "variants",
            [],
        )

        vendor = self._get_vendor()

        # ----------------------------------------------------
        # Vendor
        # ----------------------------------------------------

        validated_data["vendor"] = vendor

        # ----------------------------------------------------
        # Slug
        # ----------------------------------------------------

        validated_data["slug"] = (
            self._generate_unique_slug(
                vendor=vendor,
                name=validated_data["name"],
            )
        )

        # ----------------------------------------------------
        # Product
        # ----------------------------------------------------

        product = Product.objects.create(
            **validated_data
        )

        # ----------------------------------------------------
        # Product images
        # ----------------------------------------------------

        if images_data:
            ProductImage.objects.bulk_create(
                [
                    ProductImage(
                        product=product,
                        **image_data,
                    )
                    for image_data in images_data
                ]
            )

        # ----------------------------------------------------
        # Product options
        # ----------------------------------------------------

        product_options = []

        for option_data in options_data:
            category_option = (
                option_data["category_option"]
            )

            product_options.append(
                ProductOption(
                    product=product,
                    name=category_option.name,
                    slug=category_option.slug,
                    sort_order=category_option.sort_order,
                    is_active=True,
                )
            )

        if product_options:
            ProductOption.objects.bulk_create(
                product_options
            )

        # ----------------------------------------------------
        # Refresh product options
        # ----------------------------------------------------

        created_product_options = list(
            ProductOption.objects
            .filter(
                product_id=product.id
            )
            .order_by(
                "sort_order",
                "id",
            )
        )

        # ----------------------------------------------------
        # Product option values
        # ----------------------------------------------------

        product_values = []

        option_values_by_category_option = {}

        for (
            option_data,
            product_option,
        ) in zip(
            options_data,
            created_product_options,
        ):
            value_map = {}

            for index, value_name in enumerate(
                option_data["values"]
            ):
                product_value = ProductOptionValue(
                    option=product_option,
                    name=value_name,
                    slug=slugify(value_name),
                    sort_order=index,
                    is_active=True,
                )

                product_values.append(
                    product_value
                )

                value_map[
                    value_name.casefold()
                ] = product_value

            option_values_by_category_option[
                str(
                    option_data[
                        "category_option"
                    ].id
                )
            ] = value_map

        if product_values:
            ProductOptionValue.objects.bulk_create(
                product_values
            )

        # ----------------------------------------------------
        # Refresh values so UUID/DB state is guaranteed.
        # ----------------------------------------------------

        refreshed_values = list(
            ProductOptionValue.objects
            .filter(
                option__product_id=product.id
            )
            .select_related("option")
        )

        values_by_option = {}

        for value in refreshed_values:
            values_by_option.setdefault(
                value.option_id,
                {}
            )[
                value.name.casefold()
            ] = value

        option_values_by_category_option = {}

        for (
            option_data,
            product_option,
        ) in zip(
            options_data,
            created_product_options,
        ):
            option_values_by_category_option[
                str(
                    option_data[
                        "category_option"
                    ].id
                )
            ] = values_by_option.get(
                product_option.id,
                {},
            )

        # ----------------------------------------------------
        # Variants
        # ----------------------------------------------------

        variants_to_create = []

        variant_metadata = []

        for variant_data in variants_data:
            # Make a copy so validated_data is not unexpectedly
            # mutated while building the nested records.
            variant_data = dict(
                variant_data
            )

            option_values = variant_data.pop(
                "option_values",
                {},
            )

            images = variant_data.pop(
                "images",
                [],
            )

            variants_to_create.append(
                ProductVariant(
                    product=product,
                    **variant_data,
                )
            )

            variant_metadata.append(
                (
                    option_values,
                    images,
                )
            )

        if variants_to_create:
            ProductVariant.objects.bulk_create(
                variants_to_create
            )

        # ----------------------------------------------------
        # Refresh variants
        # ----------------------------------------------------

        created_variants = list(
            ProductVariant.objects
            .filter(
                product_id=product.id
            )
            .order_by(
                "sort_order",
                "id",
            )
        )

        # ----------------------------------------------------
        # Variant option values + images
        # ----------------------------------------------------

        through_records = []
        variant_images = []

        for (
            variant,
            metadata,
        ) in zip(
            created_variants,
            variant_metadata,
        ):
            option_values, images = metadata

            # ------------------------------------------------
            # Variant option values
            # ------------------------------------------------

            for (
                category_option_id,
                value_name,
            ) in option_values.items():

                value_map = (
                    option_values_by_category_option.get(
                        str(category_option_id),
                        {},
                    )
                )

                product_value = value_map.get(
                    value_name.casefold()
                )

                if product_value is None:
                    raise serializers.ValidationError({
                        "variants": (
                            f"Option value '{value_name}' "
                            "could not be resolved."
                        )
                    })

                through_records.append(
                    ProductVariantOptionValue(
                        variant=variant,
                        option_value=product_value,
                    )
                )

            # ------------------------------------------------
            # Variant images
            # ------------------------------------------------

            for image_data in images:
                variant_images.append(
                    ProductVariantImage(
                        variant=variant,
                        **image_data,
                    )
                )

        # ----------------------------------------------------
        # Save variant option links
        # ----------------------------------------------------

        if through_records:
            ProductVariantOptionValue.objects.bulk_create(
                through_records
            )

        # ----------------------------------------------------
        # Save variant images
        # ----------------------------------------------------

        if variant_images:
            ProductVariantImage.objects.bulk_create(
                variant_images
            )

        return product


# ============================================================
# VARIANT OUTPUT
# ============================================================


class ProductVariantSerializer(
    serializers.ModelSerializer
):
    """
    Read-only product variant representation.

    IMPORTANT:
    Uses `variant_option_values`, not `option_values`,
    so it can consume:

        variant_option_values__option_value__option

    from the optimized queryset.
    """

    option_values = serializers.SerializerMethodField()

    images = serializers.SerializerMethodField()

    primary_image = serializers.SerializerMethodField()

    effective_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    effective_compare_at_price = (
        serializers.DecimalField(
            max_digits=12,
            decimal_places=2,
            read_only=True,
        )
    )

    is_in_stock = serializers.BooleanField(
        read_only=True,
    )

    can_be_purchased = serializers.BooleanField(
        read_only=True,
    )

    has_options = serializers.BooleanField(
        read_only=True,
    )

    option_value_count = serializers.IntegerField(
        read_only=True,
    )

    option_count = serializers.IntegerField(
        read_only=True,
    )

    option_summary = serializers.CharField(
        read_only=True,
    )

    pickup_store_id = serializers.UUIDField(
        source="product.store_id",
        read_only=True,
    )

    pickup_location = serializers.ReadOnlyField(
        source="product.pickup_location",
    )

    class Meta:
        model = ProductVariant

        fields = (
            "id",
            "product",
            "name",
            "sku",

            "option_values",

            "price",
            "compare_at_price",

            "effective_price",
            "effective_compare_at_price",

            "stock_quantity",
            "track_inventory",
            "weight",

            "is_active",
            "is_default",
            "is_available",

            "is_in_stock",
            "can_be_purchased",

            "has_options",
            "option_value_count",
            "option_count",
            "option_summary",

            "pickup_store_id",
            "pickup_location",

            "sort_order",

            "images",
            "primary_image",

            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "id",
            "product",
            "option_values",
            "effective_price",
            "effective_compare_at_price",
            "is_in_stock",
            "can_be_purchased",
            "has_options",
            "option_value_count",
            "option_count",
            "option_summary",
            "pickup_store_id",
            "pickup_location",
            "images",
            "primary_image",
            "created_at",
            "updated_at",
        )

    # ========================================================
    # OPTION VALUES
    # ========================================================

    def get_option_values(self, obj):
        """
        Uses the through model because the recommended queryset
        prefetches:

            variant_option_values
                └── option_value
                       └── option

        This avoids the N+1 query problem caused by:

            obj.option_values.all()
        """

        links = list(
            obj.variant_option_values.all()
        )

        links.sort(
            key=lambda link: (
                link.option.sort_order
                if link.option
                else 0,
                link.option_value.sort_order
                if link.option_value
                else 0,
            )
        )

        return [
            {
                "id": str(link.option_value.id),

                "option": {
                    "id": str(
                        link.option.id
                    ),
                    "name": link.option.name,
                    "slug": link.option.slug,
                },

                "name": link.option_value.name,

                "slug": link.option_value.slug,
            }
            for link in links
        ]

    # ========================================================
    # IMAGES
    # ========================================================

    def _get_images(self, obj):
        images = getattr(
            obj,
            "_prefetched_variant_images",
            None,
        )

        if images is not None:
            return images

        return list(
            obj.images
            .filter(is_active=True)
            .order_by(
                "-is_primary",
                "display_order",
                "created_at",
            )
        )

    def get_images(self, obj):
        images = self._get_images(obj)

        return ProductVariantImageSerializer(
            images,
            many=True,
            context=self.context,
        ).data

    def get_primary_image(self, obj):
        images = self._get_images(obj)

        if not images:
            return None

        primary = next(
            (
                image
                for image in images
                if image.is_primary
            ),
            None,
        )

        if primary is None:
            primary = images[0]

        return ProductVariantImageSerializer(
            primary,
            context=self.context,
        ).data


# ============================================================
# PRODUCT OUTPUT
# ============================================================


class ProductSerializer(
    serializers.ModelSerializer
):
    """
    Full vendor-side product representation.
    """

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

    applicable_category_options = (
        serializers.SerializerMethodField()
    )

    class Meta:
        model = Product

        fields = (
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
        )

        read_only_fields = (
            "id",
            "vendor",
            "slug",
            "applicable_category_options",
            "options",
            "variants",
            "images",
            "created_at",
            "updated_at",
        )

    def get_applicable_category_options(self, obj):
        category = obj.category

        if category is None:
            return []

        options = getattr(
            category,
            "_active_category_options",
            None,
        )

        if options is None:
            options = (
                CategoryOption.objects
                .filter(
                    category_id=obj.category_id,
                    is_active=True,
                )
                .order_by(
                    "sort_order",
                    "name",
                )
            )

        return CategoryOptionSerializer(
            options,
            many=True,
            context=self.context,
        ).data


# ============================================================
# PRODUCT LIST
# ============================================================


class ProductListSerializer(
    serializers.ModelSerializer
):
    """
    Lightweight vendor product-list serializer.

    Does not load:
        options
        variants
        images
    """

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

        fields = (
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
        )

        read_only_fields = (
            "id",
            "slug",
            "category_name",
            "vendor_name",
            "store_name",
            "is_available",
            "created_at",
            "updated_at",
        )


# ============================================================
# PRODUCT UPDATE
# ============================================================


class ProductUpdateSerializer(
    serializers.ModelSerializer
):
    """
    Updates an existing vendor product.

    Vendor ownership cannot be changed.
    """

    class Meta:
        model = Product

        fields = (
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
        )

        read_only_fields = (
            "id",
        )

    # ========================================================
    # SKU
    # ========================================================

    def validate_sku(self, value):
        value = value.strip()

        if not value:
            return value

        queryset = (
            Product.objects
            .filter(
                vendor_id=self.instance.vendor_id,
                sku=value,
            )
            .exclude(
                pk=self.instance.pk
            )
        )

        if queryset.exists():
            raise serializers.ValidationError(
                "A product with this SKU already exists."
            )

        return value

    # ========================================================
    # STORE
    # ========================================================

    def validate_store(self, store):
        if store.vendor_id != self.instance.vendor_id:
            raise serializers.ValidationError(
                "The selected store does not belong "
                "to this vendor."
            )

        if not store.is_active:
            raise serializers.ValidationError(
                "The selected store is inactive."
            )

        return store

    # ========================================================
    # CATEGORY
    # ========================================================

    def validate_category(self, category):
        if not category.is_active:
            raise serializers.ValidationError(
                "The selected category is inactive."
            )

        return category

    # ========================================================
    # VALIDATE
    # ========================================================

    def validate(self, attrs):
        price = attrs.get(
            "price",
            self.instance.price,
        )

        compare_at_price = attrs.get(
            "compare_at_price",
            self.instance.compare_at_price,
        )

        if (
            price is not None
            and price < 0
        ):
            raise serializers.ValidationError({
                "price": (
                    "Product price cannot be negative."
                )
            })

        if (
            compare_at_price is not None
            and compare_at_price < 0
        ):
            raise serializers.ValidationError({
                "compare_at_price": (
                    "Compare-at price cannot be negative."
                )
            })

        if (
            price is not None
            and compare_at_price is not None
            and compare_at_price < price
        ):
            raise serializers.ValidationError({
                "compare_at_price": (
                    "Compare-at price cannot be lower "
                    "than the selling price."
                )
            })

        return attrs


# ============================================================
# PUBLIC PRODUCT
# ============================================================


class PublicProductSerializer(
    serializers.ModelSerializer
):
    """
    Lightweight public product serializer.

    Used by:

        GET /products/

    Does NOT serialize:
        - options
        - variants
        - variant images
    """

    images = serializers.SerializerMethodField()

    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = (
            "id",

            "name",
            "slug",
            "sku",

            "short_description",

            "price",
            "compare_at_price",

            "is_featured",
            "sort_order",

            "vendor",
            "store",
            "category",

            "images",
            "primary_image",

            "created_at",
        )

        read_only_fields = fields

    # ========================================================
    # IMAGES
    # ========================================================

    def _get_images(self, obj):
        images = getattr(
            obj,
            "_prefetched_product_images",
            None,
        )

        if images is not None:
            return images

        return list(
            obj.images
            .filter(is_active=True)
            .order_by(
                "display_order",
                "created_at",
            )
        )

    def get_images(self, obj):
        images = self._get_images(obj)

        return ProductImageSerializer(
            images,
            many=True,
            context=self.context,
        ).data

    def get_primary_image(self, obj):
        images = self._get_images(obj)

        if not images:
            return None

        primary = next(
            (
                image
                for image in images
                if image.is_primary
            ),
            None,
        )

        if primary is None:
            primary = images[0]

        return ProductImageSerializer(
            primary,
            context=self.context,
        ).data


# ============================================================
# PUBLIC PRODUCT DETAIL
# ============================================================


class PublicProductDetailSerializer(
    serializers.ModelSerializer
):
    """
    Complete public product representation.

    Used by:

        GET /products/<uuid>/

    Includes:

        Product
        ├── Images
        ├── Options
        │    └── Values
        └── Variants
             ├── Option Values
             └── Images
    """

    images = serializers.SerializerMethodField()

    primary_image = serializers.SerializerMethodField()

    options = serializers.SerializerMethodField()

    variants = serializers.SerializerMethodField()

    class Meta:
        model = Product

        fields = (
            "id",

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

            "vendor",
            "store",
            "category",

            "images",
            "primary_image",

            "options",
            "variants",

            "created_at",
            "updated_at",
        )

        read_only_fields = fields

    # ========================================================
    # PRODUCT IMAGES
    # ========================================================

    def _get_images(self, obj):
        images = getattr(
            obj,
            "_prefetched_product_images",
            None,
        )

        if images is not None:
            return images

        return list(
            obj.images
            .filter(is_active=True)
            .order_by(
                "display_order",
                "created_at",
            )
        )

    def get_images(self, obj):
        images = self._get_images(obj)

        return ProductImageSerializer(
            images,
            many=True,
            context=self.context,
        ).data

    def get_primary_image(self, obj):
        images = self._get_images(obj)

        if not images:
            return None

        primary = next(
            (
                image
                for image in images
                if image.is_primary
            ),
            None,
        )

        if primary is None:
            primary = images[0]

        return ProductImageSerializer(
            primary,
            context=self.context,
        ).data

    # ========================================================
    # OPTIONS
    # ========================================================

    def get_options(self, obj):
        options = getattr(
            obj,
            "_prefetched_options",
            None,
        )

        if options is None:
            options = list(
                obj.options
                .filter(active=True)
                .prefetch_related(
                    "values",
                )
                .order_by(
                    "sort_order",
                    "name",
                )
            )

        return ProductOptionSerializer(
            options,
            many=True,
            context=self.context,
        ).data

    # ========================================================
    # VARIANTS
    # ========================================================

    def get_variants(self, obj):
        variants = getattr(
            obj,
            "_prefetched_variants",
            None,
        )

        if variants is None:
            variants = list(
                obj.variants
                .filter(is_active=True)
                .select_related(
                    "product",
                )
                .prefetch_related(
                    "variant_option_values__option_value__option",
                    "images",
                )
                .order_by(
                    "sort_order",
                    "name",
                )
            )

        return ProductVariantSerializer(
            variants,
            many=True,
            context=self.context,
        ).data