from django.urls import include, path


urlpatterns = [

    # ============================================================
    # PRODUCT CATEGORIES
    # ============================================================

    # Public category endpoints
    #
    # GET:
    #   /api/vendors/product/categories/
    #
    # GET:
    #   /api/vendors/product/categories/<slug>/
    #
    # GET:
    #   /api/vendors/product/categories/<category-uuid>/options/
    #
    path(
        "product/categories/",
        include("vendors.urls.product_category"),
    ),


    # ============================================================
    # PRODUCT MANAGEMENT
    # ============================================================

    # Product, product images, variants and variant images
    #
    # GET/POST:
    #   /api/vendors/products/
    #
    # GET/PUT/PATCH/DELETE:
    #   /api/vendors/products/<product-uuid>/
    #
    # Product images:
    #   /api/vendors/products/<product-uuid>/images/
    #
    # Product variants:
    #   /api/vendors/products/<product-uuid>/variants/
    #
    # Variant images:
    #   /api/vendors/products/<product-uuid>/variants/
    #       <variant-uuid>/images/
    #
    path(
        "products/",
        include("vendors.urls.product"),
    ),


    # ============================================================
    # PRODUCT OPTIONS
    # ============================================================

    # Product options and product option values
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
        include("vendors.urls.product_options"),
    ),


    # ============================================================
    # VARIANT OPTION VALUE ASSIGNMENTS
    # ============================================================

    # Assign option values to a specific product variant.
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
]