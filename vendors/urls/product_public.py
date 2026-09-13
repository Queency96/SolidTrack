from django.urls import path

from vendors.views.product_public import (
    PublicProductDetailView,
    PublicProductListView,
)


urlpatterns = [
    path(
        "",
        PublicProductListView.as_view(),
        name="public-product-list",
    ),
    path(
        "<uuid:pk>/",
        PublicProductDetailView.as_view(),
        name="public-product-detail",
    ),
]


# Examples
# GET     /products/
# GET     /products/<uuid>/
#
# GET     /vendors/public/products/
# GET     /vendors/public/products/<uuid>/