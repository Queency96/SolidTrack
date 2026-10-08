from django.urls import path
from deliveries.views import (
    verify_delivery_otp,
)

urlpatterns = [
    path(
        "rider/deliveries/<uuid:delivery_id>/verify-otp/",
        verify_delivery_otp,
        name="rider-verify-delivery-otp",
    ),
]