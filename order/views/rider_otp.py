"""
Rider-facing OTP verification endpoint.

The OTP lives on the OrderFulfillment, not on the Order. Each
store's delivery has its own code. In the current architecture
(single fulfillment dispatch per order), the URL resolves to
one delivery unambiguously.
"""

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsRider
from order.models import Order, OrderFulfillment
from order.services.order_fulfillment_service import (
    OrderFulfillmentService,
)
from order.serializers.rider_otp import (
    RiderVerifyOTPRequestSerializer,
    RiderVerifyOTPResultSerializer,
)


class RiderVerifyDeliveryOTPView(generics.GenericAPIView):
    """
    Rider submits the customer's OTP to confirm handover.

    POST /api/rider/orders/<uuid>/verify-otp/

    Body:
        {"otp": "123456"}

    Preconditions
    -------------
    - Requester is authenticated and has the RIDER role.
    - Requester is the assigned rider for the order's
      delivery.
    - The fulfillment is OUT_FOR_DELIVERY.
    - The fulfillment has an unverified OTP.

    On success
    ----------
    - OrderFulfillmentService.verify_delivery_otp() handles:
        * DeliveryAssignment → COMPLETED
        * Delivery          → DELIVERED
        * Rider             → available
        * Packages          → DELIVERED
        * Fulfillment       → DELIVERED, OTP cleared
        * Order.status      → recalculated
    - Returns the final order status.
    """

    permission_classes = [IsAuthenticated, IsRider]
    serializer_class = RiderVerifyOTPRequestSerializer

    # ------------------------------------------------------
    # POST
    # ------------------------------------------------------

    def post(self, request, pk):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        submitted_otp = serializer.validated_data["otp"]

        # --------------------------------------------------
        # Load the order.
        # --------------------------------------------------

        try:
            order = (
                Order.objects
                .prefetch_related("fulfillments__delivery")
                .get(pk=pk)
            )
        except Order.DoesNotExist:
            return self._fail(
                "Order not found.",
                http_status=status.HTTP_404_NOT_FOUND,
            )

        # --------------------------------------------------
        # Resolve the delivery for this order.
        # --------------------------------------------------

        try:
            delivery = self._resolve_delivery(order=order)
        except ValueError as exc:
            return self._fail(
                str(exc),
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        if delivery is None:
            return self._fail(
                "This order does not have an active delivery.",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        # --------------------------------------------------
        # Verify and complete via the fulfillment service.
        # --------------------------------------------------

        try:
            fulfillment = (
                OrderFulfillmentService
                .verify_delivery_otp(
                    rider=request.user,
                    delivery=delivery,
                    otp=submitted_otp,
                )
            )
        except ValueError as exc:
            return self._fail(
                str(exc),
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return self._fail(
                (
                    "OTP verified, but the delivery could not "
                    f"be completed: {exc}"
                ),
                http_status=status.HTTP_409_CONFLICT,
            )

        # --------------------------------------------------
        # Return the final order state.
        # --------------------------------------------------

        order.refresh_from_db()

        result = {
            "success": True,
            "message": "Delivery confirmed.",
            "order_status": order.status,
            "delivered_at": order.delivered_at,
        }

        return Response(
            RiderVerifyOTPResultSerializer(result).data,
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------
    # Helpers
    # ------------------------------------------------------

    @staticmethod
    def _resolve_delivery(*, order):
        """
        Return the delivery for the order's single active
        fulfillment.

        In the current architecture, an order has at most one
        active fulfillment at a time. When multi-fulfillment
        dispatch lands, this method will be replaced with a
        URL-level delivery UUID.
        """

        fulfillments = list(order.fulfillments.all())

        if not fulfillments:
            return None

        active = [
            f for f in fulfillments
            if f.status not in (
                OrderFulfillment.Status.CANCELLED,
                OrderFulfillment.Status.FAILED,
            )
        ]

        if not active:
            return None

        if len(active) > 1:
            raise ValueError(
                "Order has multiple active fulfillments. "
                "Delivery UUID must be supplied."
            )

        return getattr(active[0], "delivery", None)

    @staticmethod
    def _fail(message, *, http_status):
        return Response(
            RiderVerifyOTPResultSerializer(
                {
                    "success": False,
                    "message": message,
                    "order_status": None,
                    "delivered_at": None,
                }
            ).data,
            status=http_status,
        )