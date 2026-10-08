"""
Admin fulfillment oversight views.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from order.models import OrderFulfillment, OrderItem
from order.services.order_fulfillment_service import (
    OrderFulfillmentService,
)
from wallet.models import WalletTransaction
from ..serializers.fulfillment import (
    AdminFulfillmentDetailSerializer,
    AdminFulfillmentListSerializer,
    AdminRefundSerializer,
)



class AdminFulfillmentListView(generics.ListAPIView):
    """
    List all fulfillments across vendors.

    GET /api/admin/fulfillments/

    Query params
    ------------
    ?status=<status>             Filter by fulfillment status.
    ?store=<uuid>                Filter by store.
    ?vendor=<uuid>               Filter by vendor.
    ?failed=true                 Only failed fulfillments.
    ?has_unavailable=true        Only fulfillments with
                                 UNAVAILABLE items.
    """

    permission_classes = [IsAdminUser]
    serializer_class = AdminFulfillmentListSerializer

    def get_queryset(self):
        queryset = (
            OrderFulfillment.objects
            .select_related("order", "order__customer", "store", "store__vendor")
            .prefetch_related("items")
            .order_by("-created_at")
        )

        params = self.request.query_params

        status_param = params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)

        store_id = params.get("store")
        if store_id:
            queryset = queryset.filter(store_id=store_id)

        vendor_id = params.get("vendor")
        if vendor_id:
            queryset = queryset.filter(store__vendor_id=vendor_id)

        failed = params.get("failed")
        if failed in ("true", "1"):
            queryset = queryset.filter(
                status=OrderFulfillment.Status.FAILED,
            )

        has_unavailable = params.get("has_unavailable")
        if has_unavailable in ("true", "1"):
            queryset = queryset.filter(
                items__fulfillment_status=(
                    OrderItem.FulfillmentStatus.UNAVAILABLE
                ),
            ).distinct()

        return queryset


class AdminFulfillmentDetailView(generics.RetrieveAPIView):
    """
    Retrieve one fulfillment.

    GET /api/admin/fulfillments/<uuid>/
    """

    permission_classes = [IsAdminUser]
    serializer_class = AdminFulfillmentDetailSerializer
    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        return (
            OrderFulfillment.objects
            .select_related("order", "order__customer", "store", "store__vendor")
            .prefetch_related(
                "items",
                "items__product",
                "items__variant",
                "packages",
            )
        )


class AdminRefundListView(generics.ListAPIView):
    """
    List refund wallet transactions.

    GET /api/admin/refunds/

    Query params
    ------------
    ?user=<uuid>                 Filter by customer.
    ?fulfillment=<uuid>          Filter by fulfillment
                                 (matches reference prefix).
    """

    permission_classes = [IsAdminUser]
    serializer_class = AdminRefundSerializer

    def get_queryset(self):
        queryset = (
            WalletTransaction.objects
            .filter(
                transaction_type=(
                    WalletTransaction.TransactionType.REFUND
                )
            )
            .select_related("wallet", "wallet__user")
            .order_by("-created_at")
        )

        params = self.request.query_params

        user_id = params.get("user")
        if user_id:
            queryset = queryset.filter(wallet__user_id=user_id)

        fulfillment_id = params.get("fulfillment")
        if fulfillment_id:
            queryset = queryset.filter(
                reference=f"REF-FULFILLMENT-{fulfillment_id}",
            )

        return queryset


class AdminRefundRetryView(generics.GenericAPIView):
    """
    Retry a refund for a fulfillment that has already been
    marked FAILED.

    This is a recovery path for the rare case where the refund
    transaction was never written (e.g. process died between
    fulfillment failure and refund write).

    POST /api/admin/fulfillments/<uuid>/retry-refund/

    Idempotent: if a refund already exists for this fulfillment,
    no new credit is issued.
    """

    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            fulfillment = OrderFulfillment.objects.get(pk=pk)
        except OrderFulfillment.DoesNotExist:
            return Response(
                {"detail": "Fulfillment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if fulfillment.status != OrderFulfillment.Status.FAILED:
            return Response(
                {
                    "detail": (
                        "Only FAILED fulfillments can be retried."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from common.services.refund_service import RefundService

        transaction_row = RefundService.refund_fulfillment(
            fulfillment=fulfillment,
            reason="Admin retry",
        )

        if transaction_row is None:
            return Response(
                {
                    "detail": (
                        "Refund computed to zero or already "
                        "issued. No new credit was created."
                    )
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            AdminRefundSerializer(transaction_row).data,
            status=status.HTTP_200_OK,
        )