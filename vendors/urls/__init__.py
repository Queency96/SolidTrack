from django.urls import include, path


urlpatterns = [

    # ============================================================
    # PUBLIC PRODUCT API
    # ============================================================
    #
    # Public, read-only product catalogue.
    #
    # Examples:
    #
    # GET /api/vendors/public/products/
    # GET /api/vendors/public/products/<product-uuid>/
    #
    path(
        "public/products/",
        include("vendors.urls.product_public"),
    ),


    # ============================================================
    # VENDOR PRODUCT API
    # ============================================================
    #
    # Product management:
    #
    # GET /api/vendors/products/
    # POST /api/vendors/products/
    #
    # GET /api/vendors/products/<product-uuid>/
    # PUT/PATCH/DELETE /api/vendors/products/<product-uuid>/
    #
    path(
        "products/",
        include("vendors.urls.product"),
    ),


    # ============================================================
    # PRODUCT VARIANTS
    # ============================================================
    #
    # Examples:
    #
    # GET/POST:
    #   /api/vendors/products/<product-uuid>/variants/
    #
    # GET/PUT/PATCH/DELETE:
    #   /api/vendors/products/<product-uuid>/variants/<variant-uuid>/
    #
    path(
        "products/",
        include("vendors.urls.product_variant"),
    ),


    # ============================================================
    # VARIANT OPTION VALUES
    # ============================================================
    #
    # Variant option values are nested under the variant.
    #
    # Examples:
    #
    # GET/POST:
    #   /api/vendors/products/variants/
    #       <variant-uuid>/option-values/
    #
    # GET/DELETE:
    #   /api/vendors/products/variants/
    #       <variant-uuid>/option-values/<assignment-uuid>/
    #
    path(
        "products/",
        include("vendors.urls.product_variant_option_value"),
    ),


    # ============================================================
    # PRODUCT OPTIONS / OPTION VALUES
    # ============================================================
    #
    # Product-level option management.
    #
    # Examples:
    #
    # GET/POST:
    #   /api/vendors/products/options/
    #
    # GET/PUT/PATCH/DELETE:
    #   /api/vendors/products/options/<option-uuid>/
    #
    # GET/POST:
    #   /api/vendors/products/option-values/
    #
    # GET/PUT/PATCH/DELETE:
    #   /api/vendors/products/option-values/<value-uuid>/
    #
    path(
        "products/",
        include("vendors.urls.product_option"),
    ),
]