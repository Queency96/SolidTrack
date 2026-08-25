from django.urls import path, include

urlpatterns = [
    path(
        "product/variant-option-values/",
        include(
            "vendors.urls.product_variant_option_value"
        ),
    ),

    path(
        "product/categories/",
        include("vendors.urls.product_category"),
    ),

    path(
        "products/",
        include(
            "vendors.urls.product_options"
        ),
    ),

]



# Exanmple URLs

# GET    /product/categories/
# GET    /product/categories/detail/electronics/
# GET    /approduct/categories/<id>/children/

# GET    /product/categories/admin/
# POST   /product/categories/admin/

# GET    /product/categories/admin/1/
# PUT    /product/categories/admin/1/
# PATCH  /product/categories/admin/1/
# DELETE /product/categories/admin/1/


# Product Options
# GET     /api/vendors/products/options/
# POST    /api/vendors/products/options/

# GET     /api/vendors/products/options/<id>/
# PUT     /api/vendors/products/options/<id>/
# PATCH   /api/vendors/products/options/<id>/
# DELETE  /api/vendors/products/options/<id>/