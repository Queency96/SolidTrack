"""
Vendor-facing fulfillment views.

Lets a vendor list their store's pending fulfillments and
inspect individual ones.
"""
from rest_framework.exceptions import NotFound
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Prefetch
from accounts.permissions import IsVendor
from order.models import OrderFulfillment, Package, OrderItem
from vendors.models import VendorProfile
from vendors.serializers.fulfillment import (
    VendorFulfillmentDetailSerializer,
    VendorFulfillmentListSerializer,
    VendorCannotFulfillResultSerializer,
    VendorCannotFulfillSerializer,
)
from order.services.order_fulfillment_service import (
    OrderFulfillmentService,
)



def _get_vendor(user):
    return (
        VendorProfile.objects
        .filter(user=user)
        .first()
    )


class PendingFulfillmentsView(generics.ListAPIView):
    """
    List fulfillments that are waiting to be packed or are
    currently being prepared.

    GET /api/vendors/fulfillments/pending/

    Query params
    ------------
    ?store=<store_uuid>      Restrict to a specific store.
    ?status=<status>         One of:
                                PENDING
                                PROCESSING
                                PACKING
                                READY_FOR_DISPATCH
                             Defaults to all four.
    """

    permission_classes = [IsAuthenticated, IsVendor]
    serializer_class = VendorFulfillmentListSerializer

    PENDING_STATUSES = (
        OrderFulfillment.Status.PENDING,
        OrderFulfillment.Status.PROCESSING,
        OrderFulfillment.Status.PACKING,
        OrderFulfillment.Status.READY_FOR_DISPATCH,
    )

    def get_queryset(self):
        vendor = _get_vendor(self.request.user)

        if vendor is None:
            return OrderFulfillment.objects.none()

        queryset = (
            OrderFulfillment.objects
            .filter(store__vendor=vendor)
            .filter(status__in=self.PENDING_STATUSES)
            .select_related("order", "store")
            .prefetch_related("items", "packages")
            .order_by("created_at")
        )

        store_id = self.request.query_params.get("store")

        if store_id:
            queryset = queryset.filter(store_id=store_id)

        status_param = self.request.query_params.get("status")

        if status_param and status_param in dict(
            OrderFulfillment.Status.choices
        ):
            queryset = queryset.filter(status=status_param)

        return queryset


class VendorFulfillmentDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single fulfillment belonging to the vendor.

    GET /api/vendors/fulfillments/<uuid>/
    """

    permission_classes = [IsAuthenticated, IsVendor]
    serializer_class = VendorFulfillmentDetailSerializer
    lookup_field = "pk"
    lookup_url_kwarg = "pk"

    def get_queryset(self):
        vendor = _get_vendor(self.request.user)

        if vendor is None:
            return OrderFulfillment.objects.none()

        return (
            OrderFulfillment.objects
            .filter(store__vendor=vendor)
            .select_related("order", "store")
            .prefetch_related(
                "items",
                "items__product",
                "items__variant",
                "packages",
            )
        )
    


class VendorCannotFulfillView(generics.GenericAPIView):
    """
    Vendor signals that a fulfillment (or a subset of its
    items) cannot be completed.

    POST /api/vendors/fulfillments/<uuid>/cannot-fulfill/

    Body
    ----
    {
        "reason": "Store closed due to flooding.",
        "item_ids": ["<order_item_uuid>", "..."]   // optional
    }

    When `item_ids` is omitted, every PENDING item on the
    fulfillment is marked UNAVAILABLE and the fulfillment
    transitions to FAILED.

    When `item_ids` is provided, only those items are marked
    UNAVAILABLE. Remaining items continue through normal
    packing and dispatch.

    A refund is automatically credited to the customer
    wallet, excluding perishable items per policy.
    """

    permission_classes = [IsAuthenticated, IsVendor]

    serializer_class = VendorCannotFulfillSerializer

    def get_serializer_class(self):
        # OpenAPI differentiation for request vs. response.
        if self.request.method == "POST":
            return VendorCannotFulfillSerializer
        return VendorCannotFulfillResultSerializer

    # ------------------------------------------------------
    # Queryset
    # ------------------------------------------------------

    def get_queryset(self):
        vendor = _get_vendor(self.request.user)

        if vendor is None:
            return OrderFulfillment.objects.none()

        return (
            OrderFulfillment.objects
            .filter(store__vendor=vendor)
            .select_related("order", "store")
            .prefetch_related("items", "packages")
        )

    # ------------------------------------------------------
    # POST
    # ------------------------------------------------------

    def post(self, request, pk):
        fulfillment = self._get_fulfillment(pk=pk)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reason = serializer.validated_data["reason"]
        item_ids = serializer.validated_data.get("item_ids")

        # --------------------------------------------------
        # Resolve items.
        # --------------------------------------------------

        if item_ids:
            failed_items = self._resolve_items(
                fulfillment=fulfillment,
                item_ids=item_ids,
            )
        else:
            failed_items = None

        # --------------------------------------------------
        # Snapshot pre-call state so we can report what
        # changed in the response.
        # --------------------------------------------------

        pre_unavailable_ids = set(
            fulfillment.items
            .filter(
                fulfillment_status=(
                    OrderItem.FulfillmentStatus.UNAVAILABLE
                )
            )
            .values_list("id", flat=True)
        )

        try:
            fulfillment = (
                OrderFulfillmentService
                .vendor_cannot_fulfill(
                    fulfillment=fulfillment,
                    failed_items=failed_items,
                    reason=reason,
                    failed_by=request.user,
                )
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------------------------
        # Report what changed.
        # --------------------------------------------------

        post_unavailable_ids = set(
            fulfillment.items
            .filter(
                fulfillment_status=(
                    OrderItem.FulfillmentStatus.UNAVAILABLE
                )
            )
            .values_list("id", flat=True)
        )

        newly_unavailable = post_unavailable_ids - pre_unavailable_ids

        refund_transaction = self._find_refund_transaction(
            fulfillment=fulfillment,
        )

        is_full_failure = (
            fulfillment.status
            == OrderFulfillment.Status.FAILED
        )

        result = {
            "fulfillment_status": fulfillment.status,
            "items_marked_unavailable": len(newly_unavailable),
            "refund_amount": (
                str(refund_transaction.amount)
                if refund_transaction is not None
                else None
            ),
            "refund_reference": (
                refund_transaction.reference
                if refund_transaction is not None
                else None
            ),
            "is_full_failure": is_full_failure,
        }

        response_serializer = VendorCannotFulfillResultSerializer(
            result,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------

    def _get_fulfillment(self, *, pk):
        try:
            return self.get_queryset().get(pk=pk)
        except OrderFulfillment.DoesNotExist:
            raise NotFound("Fulfillment not found.")

    def _resolve_items(self, *, fulfillment, item_ids):
        """
        Return the OrderItem instances matching item_ids.

        Enforces ownership: every item must belong to the
        fulfillment being acted on.
        """

        items = list(
            OrderItem.objects
            .filter(fulfillment=fulfillment, pk__in=item_ids)
        )

        if len(items) != len(item_ids):
            raise NotFound(
                "One or more items do not belong to this "
                "fulfillment."
            )

        return items

    @staticmethod
    def _find_refund_transaction(*, fulfillment):
        """
        Look up the refund transaction created for this
        fulfillment. Uses the deterministic idempotency
        reference defined by RefundService.
        """

        from wallet.models import WalletTransaction

        reference = f"REF-FULFILLMENT-{fulfillment.pk}"

        return (
            WalletTransaction.objects
            .filter(reference=reference)
            .first()
        )