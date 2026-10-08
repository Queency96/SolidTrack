from django.urls import path

from order.admin_urls.views.fulfillment import (
    AdminFulfillmentDetailView,
    AdminFulfillmentListView,
    AdminRefundListView,
    AdminRefundRetryView,
)


urlpatterns = [
    path(
        "fulfillments/",
        AdminFulfillmentListView.as_view(),
        name="admin-fulfillment-list",
    ),
    path(
        "fulfillments/<uuid:pk>/",
        AdminFulfillmentDetailView.as_view(),
        name="admin-fulfillment-detail",
    ),
    path(
        "fulfillments/<uuid:pk>/retry-refund/",
        AdminRefundRetryView.as_view(),
        name="admin-refund-retry",
    ),
    path(
        "refunds/",
        AdminRefundListView.as_view(),
        name="admin-refund-list",
    ),
]