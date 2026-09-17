from django.urls import path

from ..views.product_option import (
    VendorProductOptionListCreateView,
    VendorProductOptionDetailView,
    VendorProductOptionValueListCreateView,
    VendorProductOptionValueDetailView,
)


urlpatterns = [
    # ============================================================
    # PRODUCT OPTIONS
    # ============================================================

    # List and create product options
    #
    # GET  /options/
    # POST /options/
    #
    # Optional filtering:
    #
    # GET /options/?product=<product-uuid>
    #
    path(
        "options/",
        VendorProductOptionListCreateView.as_view(),
        name="vendor-product-option-list-create",
    ),

    # Retrieve, update, or delete a product option
    #
    # GET    /options/<uuid>/
    # PUT    /options/<uuid>/
    # PATCH  /options/<uuid>/
    # DELETE /options/<uuid>/
    #
    path(
        "options/<uuid:pk>/",
        VendorProductOptionDetailView.as_view(),
        name="vendor-product-option-detail",
    ),

    # ============================================================
    # PRODUCT OPTION VALUES
    # ============================================================

    # List and create option values
    #
    # GET  /option-values/
    # POST /option-values/
    #
    # Optional filtering:
    #
    # GET /option-values/?option=<option-uuid>
    #
    path(
        "option-values/",
        VendorProductOptionValueListCreateView.as_view(),
        name="vendor-product-option-value-list-create",
    ),

    # Retrieve, update, or delete an option value
    #
    # GET    /option-values/<uuid>/
    # PUT    /option-values/<uuid>/
    # PATCH  /option-values/<uuid>/
    # DELETE /option-values/<uuid>/
    #
    path(
        "option-values/<uuid:pk>/",
        VendorProductOptionValueDetailView.as_view(),
        name="vendor-product-option-value-detail",
    ),
]