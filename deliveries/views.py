from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import (IsAuthenticated)
from rest_framework.response import Response
from rest_framework import status
from accounts.permissions import (IsCustomer)
from .serializers import (DeliveryBookingSerializer, PriceEstimateSerializer)
from .services import DeliveryService, PricingService



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