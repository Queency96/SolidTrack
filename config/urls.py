from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("schema/", SpectacularAPIView.as_view(), name="schema"),

    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    #Apps URLS
    path("accounts/", include("accounts.urls")),
    path("wallet/", include("wallet.urls")),
    path("notifications/", include("notifications.urls")),
]