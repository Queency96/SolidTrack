from django.urls import include, path


urlpatterns = [
  path("rider-otp/", include("order.urls.rider_otp")),
  path("tracking/", include("order.urls.tracking")),
  path("fulfillment/", include("order.urls.fulfillment")),
]