from django.urls import path

from vendors.views.product import (
    PublicProductDetailView,
    PublicProductListView
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

from vendors.views.product_category import (
    CategoryOptionsView,
)


urlpatterns = [

    # ============================================================
    # PRODUCTS
    # ============================================================

    # List products / create product
    #
    # GET:
    #   /api/vendors/products/
    #
    # POST:
    #   /api/vendors/products/
    #
    path(
        "",
        PublicProductListView.as_view(),
        name="product-list",
    ),

    # Product availability
    #
    # GET:
    #   /api/vendors/products/availability/
    #
    path(
        "availability/",
        ProductAvailabilityView.as_view(),
        name="product-availability",
    ),

    # Product availability for a specific product
    #
    # GET:
    #   /api/vendors/products/availability/<product-uuid>/
    #
    path(
        "availability/<uuid:pk>/",
        ProductAvailabilityView.as_view(),
        name="product-availability-detail",
    ),

    # Availability check endpoint
    #
    # GET/POST depending on ProductAvailabilityView implementation.
    #
    path(
        "check/",
        ProductAvailabilityView.as_view(),
        name="product-availability-check",
    ),

    # Retrieve / update / delete a product
    #
    # GET:
    #   /api/vendors/products/<product-uuid>/
    #
    # PUT/PATCH:
    #   /api/vendors/products/<product-uuid>/
    #
    # DELETE:
    #   /api/vendors/products/<product-uuid>/
    #
    path(
        "<uuid:pk>/",
        PublicProductDetailView.as_view(),
        name="product-detail",
    ),


    # ============================================================
    # CATEGORY OPTIONS
    # ============================================================

    # Get the options available for a product category.
    #
    # Example:
    #
    # GET:
    #   /api/vendors/products/categories/<category-uuid>/options/
    #
    # Response:
    #
    # {
    #     "category": {
    #         "id": "...",
    #         "name": "Smartphones",
    #         "slug": "smartphones"
    #     },
    #     "options": [
    #         {
    #             "id": "...",
    #             "name": "Colour",
    #             "slug": "colour"
    #         },
    #         {
    #             "id": "...",
    #             "name": "Storage",
    #             "slug": "storage"
    #         }
    #     ],
    #     "count": 2
    #     }
    #
    path(
        "categories/<uuid:category_id>/options/",
        CategoryOptionsView.as_view(),
        name="category-options",
    ),


    # ============================================================
    # PRODUCT IMAGES
    # ============================================================

    # List / create images for a product
    #
    # GET:
    #   /api/vendors/products/<product-uuid>/images/
    #
    # POST:
    #   /api/vendors/products/<product-uuid>/images/
    #
    path(
        "<uuid:product_id>/images/",
        ProductImageListCreateView.as_view(),
        name="product-image-list-create",
    ),

    # Retrieve / update / delete a product image
    #
    # GET:
    #   /api/vendors/products/<product-uuid>/images/<image-uuid>/
    #
    # PUT/PATCH:
    #   /api/vendors/products/<product-uuid>/images/<image-uuid>/
    #
    # DELETE:
    #   /api/vendors/products/<product-uuid>/images/<image-uuid>/
    #
    path(
        "<uuid:product_id>/images/<uuid:pk>/",
        ProductImageDetailView.as_view(),
        name="product-image-detail",
    ),


    # ============================================================
    # PRODUCT VARIANTS
    # ============================================================

    # List / create variants for a product
    #
    # GET:
    #   /api/vendors/products/<product-uuid>/variants/
    #
    # POST:
    #   /api/vendors/products/<product-uuid>/variants/
    #
    path(
        "<uuid:product_id>/variants/",
        ProductVariantListCreateView.as_view(),
        name="product-variant-list-create",
    ),

    # Retrieve / update / delete a specific variant
    #
    # GET:
    #   /api/vendors/products/<product-uuid>/variants/<variant-uuid>/
    #
    # PUT/PATCH:
    #   /api/vendors/products/<product-uuid>/variants/<variant-uuid>/
    #
    # DELETE:
    #   /api/vendors/products/<product-uuid>/variants/<variant-uuid>/
    #
    path(
        "<uuid:product_id>/variants/<uuid:pk>/",
        ProductVariantDetailView.as_view(),
        name="product-variant-detail",
    ),


    # ============================================================
    # PRODUCT VARIANT IMAGES
    # ============================================================

    # List / create images for a variant
    #
    # GET:
    #   /api/vendors/products/<product-uuid>/variants/
    #       <variant-uuid>/images/
    #
    # POST:
    #   /api/vendors/products/<product-uuid>/variants/
    #       <variant-uuid>/images/
    #
    path(
        "<uuid:product_id>/variants/<uuid:variant_id>/images/",
        ProductVariantImageListCreateView.as_view(),
        name="product-variant-image-list-create",
    ),

    # Retrieve / update / delete a variant image
    #
    # GET:
    #   /api/vendors/products/<product-uuid>/variants/
    #       <variant-uuid>/images/<image-uuid>/
    #
    # PUT/PATCH:
    #   /api/vendors/products/<product-uuid>/variants/
    #       <variant-uuid>/images/<image-uuid>/
    #
    # DELETE:
    #   /api/vendors/products/<product-uuid>/variants/
    #       <variant-uuid>/images/<image-uuid>/
    #
    path(
        "<uuid:product_id>/variants/<uuid:variant_id>/images/<uuid:pk>/",
        ProductVariantImageDetailView.as_view(),
        name="product-variant-image-detail",
    ),
]