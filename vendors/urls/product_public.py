from django.urls import path

from vendors.views.product_public import (
    PublicProductDetailView,
    PublicProductListView,
)


urlpatterns = [
    # ============================================================
    # PUBLIC PRODUCTS
    # ============================================================

    # List publicly available products
    #
    # GET /products/
    #
    # Supported query parameters:
    #
    # ?search=iphone
    # ?category=smartphones
    # ?store=ikeja-store
    # ?vendor=<vendor-uuid>
    # ?featured=true
    # ?in_stock=true
    # ?ordering=-price
    #
    path(
        "",
        PublicProductListView.as_view(),
        name="public-product-list",
    ),

    # Retrieve a single publicly available product
    #
    # GET /products/<product-uuid>/
    #
    path(
        "<uuid:pk>/",
        PublicProductDetailView.as_view(),
        name="public-product-detail",
    ),
]