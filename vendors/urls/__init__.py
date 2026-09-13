from django.urls import include, path

urlpatterns = [
    path("public/products/", include("vendors.urls.product_public")),

    path("products/", include("vendors.urls.product")),
    path("products/", include("vendors.urls.product_variant")),
    path("products/variants/options/", include("vendors.urls.product_variant_option_value")),
    path("products/", include("vendors.urls.product_option")),
]
