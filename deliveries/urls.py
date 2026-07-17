from django.urls import path
from .views import (DeliveryBookingView, PriceEstimateView, DeliveryOfferResponseView,)




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
]