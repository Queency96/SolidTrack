from django.urls import path
from .views import (DeliveryBookingView, PriceEstimateView)




urlpatterns = [
    path(
        "book/",
        DeliveryBookingView.as_view(),
    ),
    path(
        "estimate/",
        PriceEstimateView.as_view(),
    ),
]