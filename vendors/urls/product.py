from django.urls import path

from vendors.views.product import (
    ProductDetailView,
    ProductListCreateView,
)
from vendors.views.product_availability import ProductAvailabilityView


urlpatterns = [
    path(
        "",
        ProductListCreateView.as_view(),
        name="product-list-create",
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
        ProductDetailView.as_view(),
        name="product-detail",
    ),
]



# Examples
# GET     /api/vendors/products/
# POST    /api/vendors/products/

# GET     /api/vendors/products/1/
# PUT     /api/vendors/products/1/
# PATCH   /api/vendors/products/1/
# DELETE  /api/vendors/products/1/