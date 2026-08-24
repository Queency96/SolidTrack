from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser,
)
from deliveries.models.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
)
from deliveries.serializers import (
    DeliveryOfferResponseSerializer,
    DeliveryAssignmentSerializer,
    DispatchResultSerializer,
    DeliveryOfferSerializer,
)
from deliveries.dispatch.coordinator import (
    DispatchCoordinator,
)
from deliveries.dispatch.assignment import (
    AssignmentService,
)
from rest_framework.response import Response





class DispatchDeliveryCreatedView(
    GenericAPIView,
):
    permission_classes = [
        IsAdminUser,
    ]

    serializer_class = (
        DispatchResultSerializer
    )

    def post(
        self,
        request,
        pk,
    ):
        delivery = get_object_or_404(
            Delivery,
            pk=pk,
        )

        result = (
            DispatchCoordinator.delivery_created(
                delivery
            )
        )

        serializer = self.get_serializer(
            result.to_dict()
        )

        return Response(
            serializer.data,
            status=(
                status.HTTP_200_OK
                if result.success
                else status.HTTP_400_BAD_REQUEST
            ),
        )



class DeliveryOfferResponseView(
    GenericAPIView,
):
    """
    Rider accepts or rejects
    a delivery offer.
    """

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
        )

        result = (
            DispatchCoordinator.respond_to_offer(
                offer=offer,
                action=serializer.validated_data[
                    "action"
                ],
                reason=serializer.validated_data.get(
                    "rejection_reason",
                    "",
                ),
            )
        )

        response = (
            DispatchResultSerializer(
                result,
            ).data
        )

        if result.assignment:
            response["assignment"] = (
                DeliveryAssignmentSerializer(
                    result.assignment
                ).data
            )

        return Response(
            response,
            status=status.HTTP_200_OK,
        )



class RetryDispatchView(
    GenericAPIView,
):
    """
    Retry dispatch for a delivery.
    """

    permission_classes = [
        IsAdminUser,
    ]

    def post(
        self,
        request,
        pk,
    ):
        delivery = get_object_or_404(
            Delivery,
            pk=pk,
        )

        result = (
            DispatchCoordinator.dispatch(
                delivery,
            )
        )

        return Response(
            DispatchResultSerializer(
                result,
            ).data,
            status=status.HTTP_200_OK,
        )



class DispatchDeliveryView(
    GenericAPIView,
):
    """
    Manually start dispatch.
    """

    permission_classes = [
        IsAdminUser,
    ]

    def post(
        self,
        request,
        pk,
    ):
        delivery = get_object_or_404(
            Delivery,
            pk=pk,
        )

        result = (
            DispatchCoordinator.dispatch(
                delivery,
            )
        )

        return Response(
            DispatchResultSerializer(
                result,
            ).data,
            status=status.HTTP_200_OK,
        )



class ExpireDeliveryOfferView(
    GenericAPIView,
):
    """
    Force expire a delivery offer.

    Normally handled automatically
    by Celery.
    """

    permission_classes = [
        IsAdminUser,
    ]

    def post(
        self,
        request,
        pk,
    ):
        offer = get_object_or_404(
            DeliveryOffer,
            pk=pk,
        )

        result = (
            DispatchCoordinator.offer_expired(
                offer,
            )
        )

        response = (
            DispatchResultSerializer(
                result,
            ).data
        )

        if result.assignment:
            response["assignment"] = (
                DeliveryAssignmentSerializer(
                    result.assignment
                ).data
            )

        return Response(
            response,
            status=status.HTTP_200_OK,
        )



class DeliveryAssignmentDetailView(
    GenericAPIView,
):
    """
    Retrieve assignment details.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = (
        DeliveryAssignmentSerializer
    )

    def get(
        self,
        request,
        pk,
    ):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )



class RiderCurrentAssignmentView(
    GenericAPIView,
):
    """
    Current active assignment
    for authenticated rider.
    """

    permission_classes = [
        IsAuthenticated,
    ]

    serializer_class = (
        DeliveryAssignmentSerializer
    )

    def get(
        self,
        request,
    ):
        assignment = (
            DeliveryAssignment.objects
            .filter(
                rider=request.user,
            )
            .exclude(
                status__in=[
                    DeliveryAssignment.AssignmentStatus.COMPLETED,
                    DeliveryAssignment.AssignmentStatus.CANCELLED,
                    DeliveryAssignment.AssignmentStatus.ASSIGNED,
                ]
            )
            .select_related(
                "delivery",
                "rider",
            )
            .first()
        )

        if assignment is None:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No active assignment."
                    ),
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )



class RiderAssignmentsView(GenericAPIView):
    """
    List assignments for the authenticated rider.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def get(self, request):
        assignments = (
            DeliveryAssignment.objects.filter(
                rider=request.user,
            )
            .select_related(
                "delivery",
                "rider",
                "assigned_by",
            )
            .order_by("-created_at")
        )

        serializer = self.get_serializer(
            assignments,
            many=True,
        )

        return Response(serializer.data)




class DeliveryOffersView(GenericAPIView):
    """
    List offers belonging to the authenticated rider.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryOfferSerializer

    def get(self, request):
        offers = (
            DeliveryOffer.objects.filter(
                rider=request.user,
            )
            .select_related("delivery")
            .order_by("-created_at")
        )

        return Response(
            self.get_serializer(
                offers,
                many=True,
            ).data
        )



class DeliveryOfferDetailView(GenericAPIView):
    """
    Retrieve a delivery offer.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryOfferSerializer

    def get(self, request, pk):
        offer = get_object_or_404(
            DeliveryOffer,
            pk=pk,
            rider=request.user,
        )

        return Response(
            self.get_serializer(
                offer,
            ).data
        )



class AcceptAssignmentView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.accept(
            assignment,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )


class StartPickupView(GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):

        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.start_pickup(
            assignment,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )



class ArrivePickupView(GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):

        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.arrive_pickup(
            assignment,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )



class PickupCompletedView(GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):

        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.pickup_completed(
            assignment,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )


class StartDeliveryView(GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):

        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.start_delivery(
            assignment,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )



class ArriveDestinationView(GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):

        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.arrive_destination(
            assignment,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )



class CompleteDeliveryView(GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):

        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.complete(
            assignment,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )



class CancelAssignmentView(GenericAPIView):

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):

        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        reason = request.data.get(
            "reason",
            "",
        )

        assignment = AssignmentService.cancel(
            assignment,
            reason=reason,
        )

        return Response(
            self.get_serializer(
                assignment,
            ).data
        )



