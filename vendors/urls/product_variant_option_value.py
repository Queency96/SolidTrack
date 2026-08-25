from django.urls import path

from vendors.views.product_variant_option_value import (
    ProductVariantOptionValueListCreateView,
    ProductVariantOptionValueDetailView,
)


urlpatterns = [

    path(
        "",
        ProductVariantOptionValueListCreateView.as_view(),
        name=(
            "product-variant-option-value-list-create"
        ),
    ),

    path(
        "<int:pk>/",
        ProductVariantOptionValueDetailView.as_view(),
        name=(
            "product-variant-option-value-detail"
        ),
    ),

]