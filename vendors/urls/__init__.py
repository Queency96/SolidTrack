from django.urls import include, path


urlpatterns = [

    # ============================================================
    # PUBLIC PRODUCT API (customer-facing)
    # ============================================================
    #
    # GET /api/vendors/public/products/
    # GET /api/vendors/public/products/me/
    # GET /api/vendors/public/products/<uuid>/
    #
    path(
        "public/products/",
        include("vendors.urls.product_public"),
    ),

    # ============================================================
    # VENDOR PRODUCT API
    # ============================================================
    #
    # All vendor-side product routes (base CRUD, options,
    # variants, variant option values, images) now live in a
    # single module. This eliminates four overlapping
    # includes that previously mounted the same "products/"
    # prefix and relied on Django's include ordering.
    #
    path(
        "products/",
        include("vendors.urls.product"),
    ),

    # ============================================================
    # VENDOR FULFILLMENTS
    # ============================================================
    #
    path(
        "fulfillments/",
        include("vendors.urls.fulfillments"),
    ),
]