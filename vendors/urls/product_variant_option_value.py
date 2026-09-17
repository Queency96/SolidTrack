from django.urls import path

from vendors.views.product_variant_option_value import (
    ProductVariantOptionValueListCreateView,
    ProductVariantOptionValueDetailView,
)


urlpatterns = [
    # ============================================================
    # VARIANT OPTION VALUES
    # ============================================================

    # List and assign option values to a variant
    #
    # GET:
    #   /variants/<variant-uuid>/option-values/
    #
    # POST:
    #   /variants/<variant-uuid>/option-values/
    #
    path(
        "variants/<uuid:variant_id>/option-values/",
        ProductVariantOptionValueListCreateView.as_view(),
        name="product-variant-option-value-list-create",
    ),

    # Retrieve or remove one option-value assignment
    #
    # GET:
    #   /variants/<variant-uuid>/option-values/<assignment-uuid>/
    #
    # DELETE:
    #   /variants/<variant-uuid>/option-values/<assignment-uuid>/
    #
    path(
        "variants/<uuid:variant_id>/option-values/<uuid:pk>/",
        ProductVariantOptionValueDetailView.as_view(),
        name="product-variant-option-value-detail",
    ),
]