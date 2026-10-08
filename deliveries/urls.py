from django.urls import path
from .views import (DeliveryBookingView, PriceEstimateView, DeliveryOfferResponseView, verify_delivery_otp,)



urlpatterns = [
    path(
        "book/",
        DeliveryBookingView.as_view(),
    ),
    path(
        "estimate/",
        PriceEstimateView.as_view(),
    ),

    path(
        "offers/<uuid:pk>/respond/",
        DeliveryOfferResponseView.as_view(),
        name="respond-to-offer",
    ),

    path(
        "rider/deliveries/<uuid:delivery_id>/verify-otp/",
        verify_delivery_otp,
        name="rider-verify-delivery-otp",
    ),
]
