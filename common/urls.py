from django.urls import path

from common.views import StatesListView


urlpatterns = [
    path(
        "states/",
        StatesListView.as_view(),
        name="locations-states",
    ),
]