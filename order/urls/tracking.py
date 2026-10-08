from django.urls import path

from order.views.tracking import (
    MyOrderDetailView,
    MyOrderListView,
    MyOrderTrackingView,
)


urlpatterns = [
    path(
        "list/",
        MyOrderListView.as_view(),
        name="my-order-list",
    ),
    path(
        "details/<uuid:pk>/",
        MyOrderDetailView.as_view(),
        name="my-order-detail",
    ),
    path(
        "<uuid:pk>/",
        MyOrderTrackingView.as_view(),
        name="my-order-track",
    ),
]