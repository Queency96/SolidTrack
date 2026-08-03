from django.db import transaction
from django.utils import timezone

from deliveries.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
)

from .exceptions import (
    AssignmentAlreadyExists,
    InvalidAssignmentState,
)


class AssignmentService:
    """
    Handles the complete lifecycle of a delivery assignment.
    """

    # ==================================================
    # Public API
    # ==================================================

    @classmethod
    @transaction.atomic
    def assign(
        cls,
        delivery,
        rider,
        assigned_by=None,
    ):
        """
        Create a new rider assignment.
        """
        delivery = cls._lock_delivery(
            delivery,
        )

        cls._ensure_not_assigned(
            delivery,
        )

        assignment = DeliveryAssignment.objects.create(
            delivery=delivery,
            rider=rider,
            assigned_by=assigned_by,
            status=DeliveryAssignment.AssignmentStatus.ASSIGNED,
            assigned_at=timezone.now(),
        )

        cls._update_delivery_status(
            delivery,
            Delivery.DeliveryStatus.RIDER_ASSIGNED,
        )

        cls._cancel_pending_offers(
            delivery,
            rider,
        )

        return assignment

    # ==================================================
    # Rider Accepted Assignment
    # ==================================================

    @classmethod
    @transaction.atomic
    def accept(
        cls,
        assignment,
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ASSIGNED,
        )

        return cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ACCEPTED,
            accepted_at=timezone.now(),
        )

    # ==================================================
    # Rider Heading To Pickup
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_pickup(
        cls,
        assignment,
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ACCEPTED,
        )

        return cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
        )

    # ==================================================
    # Rider Arrived Pickup
    # ==================================================

    @classmethod
    @transaction.atomic
    def arrive_pickup(
        cls,
        assignment,
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
        )

        return cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
        )

    # ==================================================
    # Package Picked Up
    # ==================================================

    @classmethod
    @transaction.atomic
    def pickup_completed(
        cls,
        assignment,
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
        )

        cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.PICKED_UP,
        )

        cls._update_delivery_status(
            assignment.delivery,
            Delivery.DeliveryStatus.IN_TRANSIT,
        )

        return assignment

    # ==================================================
    # Rider Started Delivery
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_delivery(
        cls,
        assignment,
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.PICKED_UP,
        )

        return cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.OUT_FOR_DELIVERY,
        )

    # ==================================================
    # Rider Arrived Destination
    # ==================================================

    @classmethod
    @transaction.atomic
    def arrive_destination(
        cls,
        assignment,
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.OUT_FOR_DELIVERY,
        )

        return cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ARRIVED_DESTINATION,
        )

    # ==================================================
    # Delivery Completed
    # ==================================================

    @classmethod
    @transaction.atomic
    def complete(
        cls,
        assignment,
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ARRIVED_DESTINATION,
        )

        cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.COMPLETED,
            completed_at=timezone.now(),
        )

        cls._update_delivery_status(
            assignment.delivery,
            Delivery.DeliveryStatus.DELIVERED,
        )

        return assignment

    # ==================================================
    # Cancel Assignment
    # ==================================================

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        assignment,
        reason="",
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.CANCELLED,
            cancellation_reason=reason,
        )

        return assignment

    # ==================================================
    # Reassign Rider
    # ==================================================

    @classmethod
    @transaction.atomic
    def reassign(
        cls,
        assignment,
    ):
        assignment = cls._lock_assignment(
            assignment,
        )

        cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.REASSIGNED,
        )

        return assignment

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _lock_delivery(
        delivery,
    ):
        return (
            Delivery.objects
            .select_for_update()
            .get(
                pk=delivery.pk,
            )
        )

    @staticmethod
    def _lock_assignment(
        assignment,
    ):
        return (
            DeliveryAssignment.objects
            .select_for_update()
            .select_related(
                "delivery",
                "rider",
            )
            .get(
                pk=assignment.pk,
            )
        )

    @staticmethod
    def _ensure_not_assigned(
        delivery,
    ):
        if DeliveryAssignment.objects.filter(
            delivery=delivery,
        ).exists():
            raise AssignmentAlreadyExists(
                "Delivery has already been assigned."
            )

    @staticmethod
    def _ensure_status(
        assignment,
        expected,
    ):
        if assignment.status != expected:
            raise InvalidAssignmentState(
                f"Expected '{expected}' "
                f"but got '{assignment.status}'."
            )

    @staticmethod
    def _update_assignment_status(
        assignment,
        status,
        **extra_fields,
    ):
        assignment.status = status

        update_fields = ["status"]

        for field, value in extra_fields.items():
            setattr(
                assignment,
                field,
                value,
            )
            update_fields.append(
                field,
            )

        assignment.save(
            update_fields=update_fields,
        )

        return assignment

    @staticmethod
    def _update_delivery_status(
        delivery,
        status,
    ):
        delivery.status = status

        delivery.save(
            update_fields=[
                "status",
            ],
        )

    @staticmethod
    def _cancel_pending_offers(
        delivery,
        accepted_rider,
    ):
        DeliveryOffer.objects.filter(
            delivery=delivery,
            status=DeliveryOffer.Status.PENDING,
        ).exclude(
            rider=accepted_rider,
        ).update(
            status=DeliveryOffer.Status.CANCELLED,
            responded_at=timezone.now(),
        )