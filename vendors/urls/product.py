from django.urls import path

from vendors.views.product import (
    PublicProductDetailView,
    PublicProductListView,
)
from vendors.views.product_availability import (
    ProductAvailabilityView,
)
from vendors.views.product_image import (
    ProductImageDetailView,
    ProductImageListCreateView,
)
from vendors.views.product_variant import (
    ProductVariantDetailView,
    ProductVariantListCreateView,
)
from vendors.views.product_variant_images import (
    ProductVariantImageDetailView,
    ProductVariantImageListCreateView,
)
from vendors.views.product_variant_option_value import (
    ProductVariantOptionValueListCreateView,
)
from vendors.views.product_details import (
    ProductVariantOptionValueDetailView,
)
from vendors.views.product_option import (
    VendorProductOptionListCreateView,
    VendorProductOptionDetailView,
    VendorProductOptionValueListCreateView,
    VendorProductOptionValueDetailView,
)
from vendors.views.product_category import (
    CategoryOptionsView,
)


urlpatterns = [

    # ============================================================
    # PRODUCT LIST / AVAILABILITY
    # ============================================================

    path(
        "",
        PublicProductListView.as_view(),
        name="product-list",
    ),

    path(
        "availability/",
        ProductAvailabilityView.as_view(),
        name="product-availability",
    ),

    path(
        "availability/<uuid:pk>/",
        ProductAvailabilityView.as_view(),
        name="product-availability-detail",
    ),

    path(
        "check/",
        ProductAvailabilityView.as_view(),
        name="product-availability-check",
    ),

    # ============================================================
    # CATEGORY OPTIONS
    # ============================================================

    path(
        "categories/<slug:category_slug>/options/",
        CategoryOptionsView.as_view(),
        name="category-options",
    ),

    # ============================================================
    # PRODUCT OPTIONS
    # ============================================================

    path(
        "options/",
        VendorProductOptionListCreateView.as_view(),
        name="vendor-product-option-list-create",
    ),

    path(
        "options/<uuid:pk>/",
        VendorProductOptionDetailView.as_view(),
        name="vendor-product-option-detail",
    ),

    path(
        "option-values/",
        VendorProductOptionValueListCreateView.as_view(),
        name="vendor-product-option-value-list-create",
    ),

    path(
        "option-values/<uuid:pk>/",
        VendorProductOptionValueDetailView.as_view(),
        name="vendor-product-option-value-detail",
    ),

    # ============================================================
    # VARIANT OPTION VALUES
    # ============================================================
    #
    # Declared BEFORE the "<uuid:pk>/" catch-all below because
    # "variants/" is a literal segment that must win over a
    # dynamic UUID match.
    # ============================================================

    path(
        "variants/<uuid:variant_id>/option-values/",
        ProductVariantOptionValueListCreateView.as_view(),
        name="product-variant-option-value-list-create",
    ),

    path(
        "variants/<uuid:variant_id>/option-values/<uuid:pk>/",
        ProductVariantOptionValueDetailView.as_view(),
        name="product-variant-option-value-detail",
    ),

    # ============================================================
    # PRODUCT IMAGES
    # ============================================================

    path(
        "<uuid:product_id>/images/",
        ProductImageListCreateView.as_view(),
        name="product-image-list-create",
    ),

    path(
        "<uuid:product_id>/images/<uuid:pk>/",
        ProductImageDetailView.as_view(),
        name="product-image-detail",
    ),

    # ============================================================
    # PRODUCT VARIANTS
    # ============================================================

    path(
        "<uuid:product_id>/variants/",
        ProductVariantListCreateView.as_view(),
        name="product-variant-list-create",
    ),

    path(
        "<uuid:product_id>/variants/<uuid:pk>/",
        ProductVariantDetailView.as_view(),
        name="product-variant-detail",
    ),

    # ============================================================
    # PRODUCT VARIANT IMAGES
    # ============================================================

    path(
        "<uuid:product_id>/variants/<uuid:variant_id>/images/",
        ProductVariantImageListCreateView.as_view(),
        name="product-variant-image-list-create",
    ),

    path(
        "<uuid:product_id>/variants/<uuid:variant_id>/images/<uuid:pk>/",
        ProductVariantImageDetailView.as_view(),
        name="product-variant-image-detail",
    ),

    # ============================================================
    # PRODUCT DETAIL (catch-all)
    # ============================================================
    #
    # This route MUST be last. Every route above with a literal
    # segment prefix ("availability/", "options/", "categories/",
    # "variants/", "check/") must be matched first. Otherwise
    # "options/" would be parsed as a product UUID and fail.
    # ============================================================

    path(
        "<uuid:pk>/",
        PublicProductDetailView.as_view(),
        name="product-detail",
    ),
]