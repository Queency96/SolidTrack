from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser,
)
from rest_framework.response import Response

from deliveries.models import (
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
from deliveries.dispatch.coordinator import DispatchCoordinator
from deliveries.dispatch.assignment import AssignmentService
from deliveries.dispatch.exceptions import InvalidOfferState


# ==========================================================
# Admin dispatch endpoints
# ==========================================================

class TriggerDispatchView(GenericAPIView):
    """
    Manually trigger dispatch for a delivery.

    Under the automatic flow, dispatch is already started by
    DeliveryService.create_delivery -> DispatchCoordinator.delivery_created.
    This endpoint is a manual/recovery hook for admin use.
    """

    permission_classes = [IsAdminUser]
    serializer_class = DispatchResultSerializer

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk)

        result = DispatchCoordinator.delivery_created(delivery)

        return Response(
            DispatchResultSerializer(result).data,
            status=(
                status.HTTP_200_OK
                if result.success
                else status.HTTP_400_BAD_REQUEST
            ),
        )


class DispatchDeliveryView(GenericAPIView):
    """
    Start or retry dispatch for a delivery.
    """

    permission_classes = [IsAdminUser]
    serializer_class = DispatchResultSerializer

    def post(self, request, pk):
        delivery = get_object_or_404(Delivery, pk=pk)

        result = DispatchCoordinator.dispatch(delivery)

        return Response(
            DispatchResultSerializer(result).data,
            status=(
                status.HTTP_200_OK
                if result.success
                else status.HTTP_400_BAD_REQUEST
            ),
        )


class ExpireDeliveryOfferView(GenericAPIView):
    """
    Force-expire a delivery offer.

    Normally handled automatically by a Celery worker.
    """

    permission_classes = [IsAdminUser]
    serializer_class = DispatchResultSerializer

    def post(self, request, pk):
        offer = get_object_or_404(DeliveryOffer, pk=pk)

        try:
            result = DispatchCoordinator.offer_expired(offer)

        except InvalidOfferState as exc:
            return Response(
                {
                    "success": False,
                    "message": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            DispatchResultSerializer(result).data,
            status=(
                status.HTTP_200_OK
                if result.success
                else status.HTTP_400_BAD_REQUEST
            ),
        )


# ==========================================================
# Rider offer response
# ==========================================================

class DeliveryOfferResponseView(GenericAPIView):
    """
    Rider accepts or rejects a delivery offer.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryOfferResponseSerializer

    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        offer = get_object_or_404(
            DeliveryOffer,
            pk=pk,
            rider=request.user,
        )

        result = DispatchCoordinator.respond_to_offer(
            offer=offer,
            action=serializer.validated_data["action"],
            rider=request.user,
            reason=serializer.validated_data.get(
                "rejection_reason",
                "",
            ),
        )

        return Response(
            DispatchResultSerializer(result).data,
            status=(
                status.HTTP_200_OK
                if result.success
                else status.HTTP_400_BAD_REQUEST
            ),
        )


# ==========================================================
# Rider reads
# ==========================================================

class DeliveryAssignmentDetailView(GenericAPIView):
    """
    Retrieve assignment details.

    Visibility (D2-B):
        - the rider who owns the assignment, or
        - staff / superuser.

    Customers view assignment information through the
    delivery detail endpoint, not directly here.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def get(self, request, pk):
        queryset = DeliveryAssignment.objects.all()

        if not (
            getattr(request.user, "is_staff", False)
            or getattr(request.user, "is_superuser", False)
        ):
            queryset = queryset.filter(rider=request.user)

        assignment = get_object_or_404(queryset, pk=pk)

        return Response(self.get_serializer(assignment).data)


class RiderCurrentAssignmentView(GenericAPIView):
    """
    Current active assignment for the authenticated rider.

    ASSIGNED is intentionally excluded here:

        - Before acceptance, the rider interacts with the
          assignment through their DeliveryOffer.
        - After acceptance, the assignment becomes ACCEPTED
          and appears here.

    This gives the rider a clean split:

        DeliveryOffersView          -> pre-acceptance
        RiderCurrentAssignmentView  -> post-acceptance
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def get(self, request):
        assignment = (
            DeliveryAssignment.objects
            .filter(rider=request.user)
            .exclude(
                status__in=[
                    DeliveryAssignment.AssignmentStatus.COMPLETED,
                    DeliveryAssignment.AssignmentStatus.CANCELLED,
                    DeliveryAssignment.AssignmentStatus.ASSIGNED,
                ]
            )
            .select_related("delivery", "rider", "assigned_by")
            .order_by("-assigned_at")
            .first()
        )

        if assignment is None:
            return Response(
                {
                    "success": False,
                    "message": "No active assignment.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(self.get_serializer(assignment).data)


class RiderAssignmentsView(GenericAPIView):
    """
    List assignments for the authenticated rider.

    Pagination is currently not applied.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def get(self, request):
        assignments = (
            DeliveryAssignment.objects
            .filter(rider=request.user)
            .select_related(
                "delivery",
                "rider",
                "assigned_by",
            )
            .order_by("-created_at")
        )

        return Response(
            self.get_serializer(
                assignments,
                many=True,
            ).data
        )


class DeliveryOffersView(GenericAPIView):
    """
    List offers belonging to the authenticated rider.

    Pagination is currently not applied.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryOfferSerializer

    def get(self, request):
        offers = (
            DeliveryOffer.objects
            .filter(rider=request.user)
            .select_related("delivery", "rider")
            .order_by("-created_at")
        )

        return Response(
            self.get_serializer(offers, many=True).data
        )


class DeliveryOfferDetailView(GenericAPIView):
    """
    Retrieve a delivery offer belonging to the
    authenticated rider.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryOfferSerializer

    def get(self, request, pk):
        offer = get_object_or_404(
            DeliveryOffer,
            pk=pk,
            rider=request.user,
        )

        return Response(self.get_serializer(offer).data)


# ==========================================================
# Rider assignment progression
# ==========================================================

class AcceptAssignmentView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.accept(assignment)

        return Response(self.get_serializer(assignment).data)


class StartPickupView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.start_pickup(assignment)

        return Response(self.get_serializer(assignment).data)


class ArrivePickupView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.arrive_pickup(assignment)

        return Response(self.get_serializer(assignment).data)


class PickupCompletedView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.pickup_completed(assignment)

        return Response(self.get_serializer(assignment).data)


class StartDeliveryView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.start_delivery(assignment)

        return Response(self.get_serializer(assignment).data)


class ArriveDestinationView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.arrive_destination(assignment)

        return Response(self.get_serializer(assignment).data)


class CompleteDeliveryView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
            rider=request.user,
        )

        assignment = AssignmentService.complete(assignment)

        return Response(self.get_serializer(assignment).data)


# ==========================================================
# Admin assignment cancellation
# ==========================================================

class AdminCancelAssignmentView(GenericAPIView):
    """
    Admin/staff cancellation of an active assignment.

    Riders cannot cancel assignments (D1-A).

    Cancellation requires a reason and goes through
    AssignmentService.cancel_by_admin, which is the sole
    authority for this transition and for restoring rider
    availability.
    """

    permission_classes = [IsAdminUser]
    serializer_class = DeliveryAssignmentSerializer

    def post(self, request, pk):
        assignment = get_object_or_404(
            DeliveryAssignment,
            pk=pk,
        )

        reason = request.data.get("reason", "")

        assignment = AssignmentService.cancel_by_admin(
            assignment=assignment,
            cancelled_by=request.user,
            reason=reason,
        )

        return Response(self.get_serializer(assignment).data)