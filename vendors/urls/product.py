from django.urls import path
from vendors.views.product import (
    ProductListCreateView,
    ProductDetailView,
)


urlpatterns = [
    path(
        "products/",
        ProductListCreateView.as_view(),
        name="product-list-create",
    ),

    path(
        "products/detals/<int:pk>/",
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