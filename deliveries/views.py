from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import (IsAuthenticated)
from rest_framework.response import Response
from rest_framework import status
from accounts.permissions import (IsCustomer)
from .serializers import (DeliveryBookingSerializer, PriceEstimateSerializer)
from .services import DeliveryService, PricingService
from rest_framework.generics import GenericAPIView
from deliveries.models.models import DeliveryOffer
from dispatch.assignment import AssignmentService
from dispatch.offer import DeliveryOfferService
from dispatch.serializers import DeliveryOfferResponseSerializer
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from deliveries.models.models import DeliveryOffer
from dispatch.serializers import DeliveryAssignmentSerializer
from dispatch.offer import DeliveryOfferService
from .serializers import DeliveryOfferResponseSerializer




class DeliveryBookingView(APIView):
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
                "tracking_number":
                delivery.tracking_number,
            },
            status=status.HTTP_201_CREATED,
        )





class PriceEstimateView(APIView):

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

        return Response(estimate)




class DeliveryOfferResponseView(
    GenericAPIView
):
    permission_classes = [
        IsAuthenticated,
    ]
    serializer_class = (
        DeliveryOfferResponseSerializer
    )
    def post(
        self,
        request,
        pk,
    ):
        serializer = self.get_serializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )
        offer = get_object_or_404(
            DeliveryOffer,
            pk=pk,
            rider=request.user,
            status=DeliveryOffer.Status.PENDING,
        )
        result = DispatchCoordinator.respond_to_offer(
            offer=offer,
            action=action,
            reason=reason,
        )

        if result["status"] == "accepted":

            return Response(
                {
                    "success": True,
                    "assignment":
                    DeliveryAssignmentSerializer(
                        result["assignment"]
                    ).data,
                }
            )

        return Response(
            {
                "success": True,
            }
        )