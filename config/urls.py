from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)


urlpatterns = [

    # ============================================================
    # Admin
    # ============================================================

    path("admin/", admin.site.urls),

    # ============================================================
    # API Schema + Docs
    # ============================================================

    path(
        "schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),

    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    # ============================================================
    # Apps
    # ============================================================

    path("accounts/", include("accounts.urls")),
    path("wallet/", include("wallet.urls")),
    path("notifications/", include("notifications.urls")),

    # ============================================================
    # Vendors
    # ============================================================
    #
    # All vendor-owned API routes are mounted under
    # "vendors/" via the package at vendors/urls/__init__.py.
    #
    # Public product catalogue: /api/vendors/public/products/
    # Vendor product CRUD:      /api/vendors/products/
    # Vendor fulfillments:      /api/vendors/fulfillments/
    #
    path("vendors/", include("vendors.urls")),

    # ------------------------------------------------------------
    # Public category endpoints (Decision A2)
    # ------------------------------------------------------------
    #
    # Category routes remain at the root because existing
    # clients reference them without the "vendors/" prefix.
    #
    # GET /api/categories/
    # GET /api/categories/<slug>/
    # GET /api/categories/<slug>/options/
    # GET/POST /api/categories/admin/
    # GET/PUT/PATCH/DELETE /api/categories/admin/<uuid>/
    #
    path("", include("vendors.urls.product_category")),

    # ============================================================
    # Customers
    # ============================================================

    path("customers/", include("customers.urls")),

    # ============================================================
    # Locations
    # ============================================================

    path("locations/", include("common.urls")),

    # ============================================================
    # Orders
    # ============================================================

    path("orders/", include("order.urls")),

    # ============================================================
    # Admin order API
    # ============================================================

    path("admin/order/", include("order.admin_urls.fulfillment")),
]