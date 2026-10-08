from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)


urlpatterns = [
    path("admin/", admin.site.urls),

    path("schema/", SpectacularAPIView.as_view(), name="schema",),

    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # Apps
    path("accounts/", include("accounts.urls")),
    path("wallet/", include("wallet.urls")),
    path("notifications/", include("notifications.urls")),

    # Vendors
    path("vendors/", include("vendors.urls")),
    path("", include("vendors.urls.product_category")),
    path("products/", include("vendors.urls.product_public")),
    path("vendors/fulfillments/", include("vendors.urls.fulfillments")),

    # Customers
    path("customers/", include("customers.urls")),

    # Locations
    path("locations/", include("common.urls")),

    # Orders
    path("orders/", include("order.urls")),

    # Order administration API
    path("admin/order/", include("order.admin_urls.fulfillment")),
]