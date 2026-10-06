from django.urls import path

from vendors.views.product_public import (
    MyStateProductListView,
    PublicProductDetailView,
    PublicProductListView,
)


urlpatterns = [
    # Guest list — no state filter
    #
    # GET /vendors/public/products/
    #
    path(
        "",
        PublicProductListView.as_view(),
        name="public-product-list",
    ),

    # Authenticated list — state-filtered
    #
    # GET /vendors/public/products/me/
    #
    path(
        "me/",
        MyStateProductListView.as_view(),
        name="public-product-list-me",
    ),

    # Detail — shared
    #
    # GET /vendors/public/products/<uuid>/
    #
    path(
        "<uuid:pk>/",
        PublicProductDetailView.as_view(),
        name="public-product-detail",
    ),
]




# if not authenticated:
#     GET BASE_URLS/vendors/public/products/        # guest list, no filter
#     render state selector as optional hint (from /api/locations/states/)

# else:
#     GET BASE_URLS/vendors/public/products/me/
#     if meta.state_source == "none":
#         render "Select your state" + open dropdown
#     elif meta.has_products_in_state == false:
#         render "No products in {meta.state_name} yet" + "Choose another state"
#     else:
#         render list

#     dropdown from GET BASE_URLS/locations/states/
#     on select: GET BASE_URLS/vendors/public/products/me/?state=<code>