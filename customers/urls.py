from django.urls import path
from .views import CustomerProfileView, UserLocationProductListView

urlpatterns = [
    path(
        "profile/",
        CustomerProfileView.as_view(),
    ),

    path(
        "products/",
        UserLocationProductListView.as_view(),
        name="user-location-products",
    ),
]