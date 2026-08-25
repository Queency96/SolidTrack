from django.urls import path
from vendors.views.product_variant import (
    ProductVariantListCreateView,
    ProductVariantDetailView,
)


urlpatterns = [
    path(
        "products/<int:product_id>/variants/",
        ProductVariantListCreateView.as_view(),
        name="product-variant-list-create",
    ),

    path(
        "products/<int:product_id>/variants/<int:pk>/",
        ProductVariantDetailView.as_view(),
        name="product-variant-detail",
    ),
]