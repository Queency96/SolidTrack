from django.contrib import admin

from .models import (
    Product,
    ProductCategory,
    ProductImage,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    ProductVariantImage,
    ProductVariantOptionValue,
)
from .models.vendor_profile import VendorProfile
from .models.store import VendorStore


# ==================================================
# Vendor Profile
# ==================================================

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for vendor profiles.
    """

    search_fields = [
        "business_name",
    ]


# ==================================================
# Vendor Store
# ==================================================

@admin.register(VendorStore)
class VendorStoreAdmin(admin.ModelAdmin):
    """
    Admin configuration for vendor stores.
    """

    search_fields = [
        "name",
        "address",
    ]

# ==================================================
# Product Category
# ==================================================

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    """
    Admin configuration for product categories.
    """

    list_display = [
        "name",
        "parent",
        "sort_order",
        "is_active",
        "product_count",
        "active_product_count",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "parent",
    ]

    search_fields = [
        "name",
        "slug",
        "description",
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }

    ordering = [
        "sort_order",
        "name",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "product_count",
        "active_product_count",
    ]

    fieldsets = [
        (
            "Category Information",
            {
                "fields": [
                    "name",
                    "slug",
                    "parent",
                    "description",
                ],
            },
        ),
        (
            "Display",
            {
                "fields": [
                    "image",
                    "sort_order",
                ],
            },
        ),
        (
            "Status",
            {
                "fields": [
                    "is_active",
                ],
            },
        ),
        (
            "Statistics",
            {
                "fields": [
                    "product_count",
                    "active_product_count",
                ],
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ],
            },
        ),
    ]


# ==================================================
# Product Images
# ==================================================

class ProductImageInline(admin.TabularInline):
    """
    Manage product images directly from Product admin.
    """

    model = ProductImage

    extra = 1

    fields = [
        "image",
        "alt_text",
        "is_primary",
        "display_order",
        "is_active",
    ]

    ordering = [
        "display_order",
        "created_at",
    ]


# ==================================================
# Product Options
# ==================================================

class ProductOptionInline(admin.TabularInline):
    """
    Manage product options directly from Product admin.
    """

    model = ProductOption

    extra = 1

    fields = [
        "name",
        "slug",
        "sort_order",
        "is_active",
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }

    ordering = [
        "sort_order",
        "name",
    ]


# ==================================================
# Product Variants
# ==================================================

class ProductVariantInline(admin.TabularInline):
    """
    Manage product variants directly from Product admin.
    """

    model = ProductVariant

    extra = 1

    fields = [
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
    ]

    ordering = [
        "sort_order",
        "created_at",
    ]


# ==================================================
# Product
# ==================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin configuration for products.
    """

    list_display = [
        "name",
        "vendor",
        "store",
        "category",
        "price",
        "stock_quantity",
        "is_active",
        "is_published",
        "is_featured",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "is_published",
        "is_featured",
        "track_inventory",
        "store",
        "category",
    ]

    search_fields = [
        "name",
        "slug",
        "sku",
        "short_description",
        "description",
        "vendor__business_name",
        "store__name",
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }

    autocomplete_fields = [
        "vendor",
        "store",
        "category",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "pickup_store",
        "pickup_location",
        "is_in_stock",
        "is_available",
    ]

    inlines = [
        ProductImageInline,
        ProductOptionInline,
        ProductVariantInline,
    ]

    ordering = [
        "sort_order",
        "-created_at",
    ]

    fieldsets = [
        (
            "Ownership",
            {
                "fields": [
                    "vendor",
                    "store",
                    "category",
                ],
            },
        ),
        (
            "Product Identity",
            {
                "fields": [
                    "name",
                    "slug",
                    "sku",
                ],
            },
        ),
        (
            "Description",
            {
                "fields": [
                    "short_description",
                    "description",
                ],
            },
        ),
        (
            "Pricing",
            {
                "fields": [
                    "price",
                    "compare_at_price",
                ],
            },
        ),
        (
            "Inventory",
            {
                "fields": [
                    "stock_quantity",
                    "track_inventory",
                    "is_in_stock",
                ],
            },
        ),
        (
            "Status",
            {
                "fields": [
                    "is_active",
                    "is_published",
                    "is_featured",
                ],
            },
        ),
        (
            "Ordering",
            {
                "fields": [
                    "sort_order",
                ],
            },
        ),
        (
            "Pickup",
            {
                "fields": [
                    "pickup_store",
                    "pickup_location",
                ],
            },
        ),
        (
            "Availability",
            {
                "fields": [
                    "is_available",
                ],
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ],
            },
        ),
    ]


# ==================================================
# Product Option Values
# ==================================================

class ProductOptionValueInline(admin.TabularInline):
    """
    Manage option values directly from ProductOption.
    """

    model = ProductOptionValue

    extra = 1

    fields = [
        "name",
        "slug",
        "sort_order",
        "is_active",
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }

    ordering = [
        "sort_order",
        "name",
    ]


# ==================================================
# Product Option
# ==================================================

@admin.register(ProductOption)
class ProductOptionAdmin(admin.ModelAdmin):
    """
    Admin configuration for product options.
    """

    list_display = [
        "name",
        "product",
        "slug",
        "sort_order",
        "is_active",
        "value_count",
        "active_value_count",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "product",
    ]

    search_fields = [
        "name",
        "slug",
        "product__name",
        "product__sku",
    ]

    autocomplete_fields = [
        "product",
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }

    readonly_fields = [
        "created_at",
        "updated_at",
        "value_count",
        "active_value_count",
        "has_values",
    ]

    inlines = [
        ProductOptionValueInline,
    ]

    ordering = [
        "sort_order",
        "name",
    ]


# ==================================================
# Product Option Value
# ==================================================

@admin.register(ProductOptionValue)
class ProductOptionValueAdmin(admin.ModelAdmin):
    """
    Admin configuration for product option values.
    """

    list_display = [
        "name",
        "option",
        "product",
        "slug",
        "sort_order",
        "is_active",
        "is_available",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "option",
    ]

    search_fields = [
        "name",
        "slug",
        "option__name",
        "option__product__name",
    ]

    autocomplete_fields = [
        "option",
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }

    readonly_fields = [
        "product",
        "product_id",
        "is_available",
        "created_at",
        "updated_at",
    ]

    ordering = [
        "sort_order",
        "name",
    ]


# ==================================================
# Product Variant Images
# ==================================================

class ProductVariantImageInline(admin.TabularInline):
    """
    Manage variant images directly from ProductVariant.
    """

    model = ProductVariantImage

    extra = 1

    fields = [
        "image",
        "alt_text",
        "is_primary",
        "display_order",
        "is_active",
    ]

    ordering = [
        "display_order",
        "created_at",
    ]


# ==================================================
# Product Variant Option Values
# ==================================================

class ProductVariantOptionValueInline(admin.TabularInline):
    """
    Manage option values assigned to a variant.
    """

    model = ProductVariantOptionValue

    extra = 1

    fields = [
        "option_value",
        "option",
        "value",
        "created_at",
    ]

    readonly_fields = [
        "option",
        "value",
        "created_at",
    ]

    autocomplete_fields = [
        "option_value",
    ]

    ordering = [
        "option_value__option__sort_order",
        "option_value__sort_order",
    ]


# ==================================================
# Product Variant
# ==================================================

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    """
    Admin configuration for product variants.
    """

    list_display = [
        "name",
        "product",
        "sku",
        "effective_price",
        "stock_quantity",
        "weight",
        "is_active",
        "is_default",
        "option_summary",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "is_default",
        "track_inventory",
        "product",
    ]

    search_fields = [
        "name",
        "sku",
        "product__name",
        "product__sku",
        "option_values__name",
    ]

    autocomplete_fields = [
        "product",
    ]

    readonly_fields = [
        "effective_price",
        "effective_compare_at_price",
        "is_in_stock",
        "is_available",
        "selected_option_values",
        "option_value_count",
        "option_count",
        "has_options",
        "option_summary",
        "pickup_store",
        "pickup_location",
        "created_at",
        "updated_at",
    ]

    inlines = [
        ProductVariantOptionValueInline,
        ProductVariantImageInline,
    ]

    ordering = [
        "sort_order",
        "created_at",
    ]

    fieldsets = [
        (
            "Product",
            {
                "fields": [
                    "product",
                ],
            },
        ),
        (
            "Variant Identity",
            {
                "fields": [
                    "name",
                    "sku",
                ],
            },
        ),
        (
            "Pricing",
            {
                "fields": [
                    "price",
                    "compare_at_price",
                    "effective_price",
                    "effective_compare_at_price",
                ],
            },
        ),
        (
            "Inventory",
            {
                "fields": [
                    "stock_quantity",
                    "track_inventory",
                    "is_in_stock",
                ],
            },
        ),
        (
            "Physical Information",
            {
                "fields": [
                    "weight",
                ],
            },
        ),
        (
            "Status",
            {
                "fields": [
                    "is_active",
                    "is_default",
                ],
            },
        ),
        (
            "Ordering",
            {
                "fields": [
                    "sort_order",
                ],
            },
        ),
        (
            "Options",
            {
                "fields": [
                    "selected_option_values",
                    "option_value_count",
                    "option_count",
                    "has_options",
                    "option_summary",
                ],
            },
        ),
        (
            "Pickup",
            {
                "fields": [
                    "pickup_store",
                    "pickup_location",
                ],
            },
        ),
        (
            "Availability",
            {
                "fields": [
                    "is_available",
                ],
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ],
            },
        ),
    ]


# ==================================================
# Product Image
# ==================================================

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    """
    Admin configuration for product images.
    """

    list_display = [
        "product",
        "is_primary",
        "display_order",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_primary",
        "is_active",
    ]

    search_fields = [
        "product__name",
        "product__sku",
        "alt_text",
    ]

    autocomplete_fields = [
        "product",
    ]

    ordering = [
        "display_order",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]


# ==================================================
# Product Variant Image
# ==================================================

@admin.register(ProductVariantImage)
class ProductVariantImageAdmin(admin.ModelAdmin):
    """
    Admin configuration for variant images.
    """

    list_display = [
        "variant",
        "is_primary",
        "display_order",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_primary",
        "is_active",
    ]

    search_fields = [
        "variant__name",
        "variant__sku",
        "variant__product__name",
        "alt_text",
    ]

    autocomplete_fields = [
        "variant",
    ]

    ordering = [
        "display_order",
        "created_at",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]


# ==================================================
# Product Variant Option Value
# ==================================================

@admin.register(ProductVariantOptionValue)
class ProductVariantOptionValueAdmin(admin.ModelAdmin):
    """
    Admin configuration for variant option assignments.
    """

    list_display = [
        "variant",
        "option_name",
        "value_name",
        "product",
        "created_at",
    ]

    list_filter = [
        "option_value__option",
        "variant__product",
    ]

    search_fields = [
        "variant__name",
        "variant__sku",
        "variant__product__name",
        "option_value__name",
        "option_value__option__name",
    ]

    autocomplete_fields = [
        "variant",
        "option_value",
    ]

    readonly_fields = [
        "option",
        "product",
        "value",
        "option_name",
        "value_name",
        "display_name",
        "created_at",
    ]

    ordering = [
        "option_value__option__sort_order",
        "option_value__sort_order",
    ]



