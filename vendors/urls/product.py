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

# NOTE: module name is singular ("product_variant_image").
# The previous import referenced "product_variant_images"
# (plural), which does not exist.
from vendors.views.product_variant_images import (
    ProductVariantImageDetailView,
    ProductVariantImageListCreateView,
)

from vendors.views.product_variant_option_value import (
    ProductVariantOptionValueListCreateView,
)

from vendors.views.product_category import (
    CategoryOptionsView,
)


urlpatterns = [

    # ============================================================
    # PRODUCTS
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

    path(
        "<uuid:pk>/",
        PublicProductDetailView.as_view(),
        name="product-detail",
    ),

    # ============================================================
    # CATEGORY OPTIONS
    # ============================================================

    path(
        "categories/<uuid:category_id>/options/",
        CategoryOptionsView.as_view(),
        name="category-options",
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
]