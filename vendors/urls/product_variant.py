from django.urls import path

from vendors.views.product_variant import (
    ProductVariantListCreateView,
    ProductVariantDetailView,
)


urlpatterns = [
    # ============================================================
    # PRODUCT VARIANTS
    # ============================================================

    # List and create variants for a product
    #
    # GET:
    #   /products/<product-uuid>/variants/
    #
    # POST:
    #   /products/<product-uuid>/variants/
    #
    path(
        "products/<uuid:product_id>/variants/",
        ProductVariantListCreateView.as_view(),
        name="product-variant-list-create",
    ),

    # Retrieve, update, or delete a specific variant
    #
    # GET:
    #   /products/<product-uuid>/variants/<variant-uuid>/
    #
    # PUT:
    #   /products/<product-uuid>/variants/<variant-uuid>/
    #
    # PATCH:
    #   /products/<product-uuid>/variants/<variant-uuid>/
    #
    # DELETE:
    #   /products/<product-uuid>/variants/<variant-uuid>/
    #
    path(
        "products/<uuid:product_id>/variants/<uuid:pk>/",
        ProductVariantDetailView.as_view(),
        name="product-variant-detail",
    ),
]