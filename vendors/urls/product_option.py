from django.urls import path

from ..views.product_option import (
    VendorProductOptionListCreateView,
    VendorProductOptionDetailView,
    VendorProductOptionValueListCreateView,
    VendorProductOptionValueDetailView,
)


urlpatterns = [

    # ==================================================
    # Product Options
    # ==================================================

    path(
        "options/",
        VendorProductOptionListCreateView.as_view(),
        name="vendor-product-option-list-create",
    ),

    path(
        "options/<int:pk>/",
        VendorProductOptionDetailView.as_view(),
        name="vendor-product-option-detail",
    ),

    # ==================================================
    # Product Option Values
    # ==================================================

    path(
        "vendors/option-values/",
        VendorProductOptionValueListCreateView.as_view(),
        name="vendor-product-option-value-list-create",
    ),

    path(
        "vendors/option-values/<int:pk>/",
        VendorProductOptionValueDetailView.as_view(),
        name="vendor-product-option-value-detail",
    ),
]


# Example API
# GET     /vendors/products/options/
# POST    /vendors/products/options/
# GET     /vendors/products/option-values/?option=5

# GET     /vendors/products/options/<id>/
# PUT     /vendors/products/options/<id>/
# PATCH   /vendors/products/options/<id>/
# DELETE  /vendors/products/options/<id>/