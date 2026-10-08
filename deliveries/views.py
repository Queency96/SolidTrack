from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
import logging
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from order.models import Order
from deliveries.models import Delivery, DeliveryAssignment
from deliveries.dispatch.assignment import AssignmentService
from accounts.permissions import IsCustomer
from deliveries.models import DeliveryOffer
from deliveries.dispatch.coordinator import DispatchCoordinator
from deliveries.dispatch.serializers import (
    DeliveryAssignmentSerializer,
    DeliveryOfferResponseSerializer,
    DispatchResultSerializer,
)
from order.services.order_fulfillment_service import OrderFulfillmentService
from .serializers import (
    DeliveryBookingSerializer,
    PriceEstimateSerializer,
)
from .services import (
    DeliveryService,
    PricingService,
)


logger = logging.getLogger(__name__)

MAX_OTP_ATTEMPTS = 5





# ==========================================================
# Delivery Booking
# ==========================================================

class DeliveryBookingView(APIView):
    """
    Customer delivery booking endpoint.

    POST /deliveries/book/
    """

    permission_classes = (
        IsAuthenticated,
        IsCustomer,
    )

    def post(self, request):
        serializer = DeliveryBookingSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        delivery = DeliveryService.create_delivery(
            request.user,
            serializer.validated_data,
        )

        return Response(
            {
                "success": True,
                "tracking_number": delivery.tracking_number,
            },
            status=status.HTTP_201_CREATED,
        )


# ==========================================================
# Price Estimate
# ==========================================================

class PriceEstimateView(APIView):
    """
    Calculate an estimated delivery price.

    POST /deliveries/price-estimate/
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = PriceEstimateSerializer(
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)

        estimate = PricingService.estimate(
            serializer.validated_data,
        )

        return Response(estimate, status=status.HTTP_200_OK)


# ==========================================================
# Delivery Offer Response
# ==========================================================

class DeliveryOfferResponseView(GenericAPIView):
    """
    Allow an authenticated rider to respond to
    their own pending delivery offer.
    """

    permission_classes = (IsAuthenticated,)

    serializer_class = DeliveryOfferResponseSerializer

    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        rejection_reason = serializer.validated_data.get(
            "rejection_reason",
            "",
        )

        # Fetch the rider's own offer (any status) so we can
        # surface a meaningful 400 from the coordinator when
        # the offer is no longer PENDING.
        offer = get_object_or_404(
            DeliveryOffer,
            pk=pk,
            rider=request.user,
        )

        result = DispatchCoordinator.respond_to_offer(
            offer=offer,
            action=action,
            rider=request.user,
            reason=rejection_reason,
        )

        response_data = DispatchResultSerializer(
            result,
            context={"request": request},
        ).data

        if result.success:
            return Response(
                response_data,
                status=status.HTTP_200_OK,
            )

        return Response(
            response_data,
            status=status.HTTP_400_BAD_REQUEST,
        )



@require_POST
def verify_delivery_otp(request, delivery_id):
    """
    Rider confirms handover by entering the OTP the
    customer received for this delivery.

    Body:
        otp: "123456"

    Each rider can only verify deliveries assigned to
    them.
    """

    rider = request.user

    if not getattr(rider, "is_authenticated", False):

        return JsonResponse(
            {"error": "Authentication required."},
            status=401,
        )

    try:

        delivery = (
            Delivery.objects
            .only("id", "fulfillment_id")
            .get(pk=delivery_id)
        )

    except Delivery.DoesNotExist:

        return JsonResponse(
            {"error": "Delivery not found."},
            status=404,
        )

    otp = (request.POST.get("otp") or "").strip()

    if not otp:

        return JsonResponse(
            {"error": "OTP is required."},
            status=400,
        )

    try:

        OrderFulfillmentService.verify_delivery_otp(
            rider=rider,
            delivery=delivery,
            otp=otp,
        )

    except ValueError as exc:

        return JsonResponse(
            {"error": str(exc)},
            status=400,
        )

    except Exception:

        logger.exception(
            "OTP verification failed for delivery %s.",
            delivery_id,
        )

        return JsonResponse(
            {"error": "Verification failed."},
            status=500,
        )

    return JsonResponse(
        {
            "status": True,
            "message": "Delivery confirmed.",
        },
        status=200,
    )