from django.urls import path

from order.views.rider_otp import (
    RiderVerifyDeliveryOTPView,
)


urlpatterns = [
    path(
        "<uuid:pk>/verify-otp/",
        RiderVerifyDeliveryOTPView.as_view(),
        name="rider-verify-otp",
    ),
]