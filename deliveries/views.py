from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.permissions import IsCustomer
from deliveries.models import DeliveryOffer
from dispatch.coordinator import DispatchCoordinator
from dispatch.serializers import (
    DeliveryAssignmentSerializer,
    DeliveryOfferResponseSerializer,
)
from .serializers import (
    DeliveryBookingSerializer,
    PriceEstimateSerializer,
)
from .services import (
    DeliveryService,
    PricingService,
)


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
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        delivery = DeliveryService.create_delivery(
            request.user,
            serializer.validated_data,
        )

        return Response(
            {
                "success": True,
                "tracking_number": (
                    delivery.tracking_number
                ),
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

    permission_classes = (
        IsAuthenticated,
    )

    def post(self, request):
        serializer = PriceEstimateSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        estimate = PricingService.estimate(
            serializer.validated_data
        )

        return Response(
            estimate,
            status=status.HTTP_200_OK,
        )


# ==========================================================
# Delivery Offer Response
# ==========================================================

from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from deliveries.models.delivery_offer import DeliveryOffer

from dispatch.coordinator import DispatchCoordinator
from dispatch.serializers import (
    DeliveryAssignmentSerializer,
    DeliveryOfferResponseSerializer,
)




class DeliveryOfferResponseView(
    GenericAPIView,
):
    """
    Allow an authenticated rider to respond to
    their own pending delivery offer.
    """

    permission_classes = (
        IsAuthenticated,
    )

    serializer_class = (
        DeliveryOfferResponseSerializer
    )

    def post(
        self,
        request,
        pk,
    ):
        # --------------------------------------------------
        # Validate request
        # --------------------------------------------------

        serializer = self.get_serializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        action = serializer.validated_data[
            "action"
        ]

        rejection_reason = (
            serializer.validated_data.get(
                "rejection_reason",
                "",
            )
        )

        # --------------------------------------------------
        # Get rider's own pending offer
        # --------------------------------------------------

        offer = get_object_or_404(
            DeliveryOffer,
            pk=pk,
            rider=request.user,
            status=(
                DeliveryOffer.Status.PENDING
            ),
        )

        # --------------------------------------------------
        # Process through coordinator
        # --------------------------------------------------

        result = (
            DispatchCoordinator
            .respond_to_offer(
                offer=offer,
                action=action,
                reason=rejection_reason,
            )
        )

        # --------------------------------------------------
        # Serialize standardized result
        # --------------------------------------------------

        response_data = (
            DispatchResultSerializer(
                result,
                context={
                    "request": request,
                },
            ).data
        )

        # --------------------------------------------------
        # HTTP status
        # --------------------------------------------------

        if result.success:
            return Response(
                response_data,
                status=status.HTTP_200_OK,
            )

        return Response(
            response_data,
            status=status.HTTP_400_BAD_REQUEST,
        )