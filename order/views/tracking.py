"""
Customer-facing order tracking views.
"""

from django.db.models import Prefetch
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from order.models import (
    Order,
    OrderFulfillment,
    OrderItem,
)

from order.serializers.tracking import (
    TrackingOrderDetailSerializer,
    TrackingOrderListSerializer,
)


class MyOrderListView(generics.ListAPIView):
    """
    List orders belonging to the authenticated customer.

    GET /api/orders/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TrackingOrderListSerializer

    ordering = ["-created_at"]

    def get_queryset(self):
        return (
            Order.objects
            .filter(customer=self.request.user)
            .prefetch_related("fulfillments", "items")
            .order_by("-created_at")
        )


class MyOrderDetailView(generics.RetrieveAPIView):
    """
    Retrieve one order belonging to the authenticated customer.

    GET /api/orders/<uuid>/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TrackingOrderDetailSerializer
    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return (
            Order.objects
            .filter(customer=self.request.user)
            .prefetch_related(
                "items",
                Prefetch(
                    "fulfillments",
                    queryset=(
                        OrderFulfillment.objects
                        .select_related("store")
                        .prefetch_related(
                            "items",
                            "delivery__assignment__rider__location",
                        )
                    ),
                ),
            )
        )


class MyOrderTrackingView(generics.RetrieveAPIView):
    """
    Live tracking endpoint.

    GET /api/orders/<uuid>/track/

    Returns the same shape as the detail endpoint, but
    explicitly designed for polling. The frontend should
    poll this endpoint every N seconds while an order is in
    an active delivery state.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TrackingOrderDetailSerializer
    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        # Same queryset as the detail view.
        return MyOrderDetailView().get_queryset()