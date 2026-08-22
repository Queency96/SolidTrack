from django.db import transaction
from django.utils import timezone
from deliveries.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
)
from riders.models import RiderProfile
from .exceptions import (
    AssignmentAlreadyExists,
    InvalidAssignmentState,
)


class AssignmentService:
    """
    Handles the complete lifecycle of a delivery assignment.

    Responsibilities
    ----------------
    • Create assignments
    • Accept assignments
    • Move riders through delivery states
    • Complete deliveries
    • Cancel assignments
    • Validate reassignment
    • Update delivery status
    • Manage rider availability
    • Cancel competing delivery offers
    • Trigger assignment notifications

    This service owns assignment state transitions.
    """

    ACTIVE_ASSIGNMENT_STATUSES = (
        DeliveryAssignment.AssignmentStatus.ASSIGNED,
        DeliveryAssignment.AssignmentStatus.ACCEPTED,
        DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
        DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
        DeliveryAssignment.AssignmentStatus.PICKED_UP,
        DeliveryAssignment.AssignmentStatus.OUT_FOR_DELIVERY,
        DeliveryAssignment.AssignmentStatus.ARRIVED_DESTINATION,
    )

    CANCELLABLE_STATUSES = (
        DeliveryAssignment.AssignmentStatus.ASSIGNED,
        DeliveryAssignment.AssignmentStatus.ACCEPTED,
        DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
        DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
        DeliveryAssignment.AssignmentStatus.PICKED_UP,
        DeliveryAssignment.AssignmentStatus.OUT_FOR_DELIVERY,
        DeliveryAssignment.AssignmentStatus.ARRIVED_DESTINATION,
    )

    # ==================================================
    # Assign
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

        Delivery:
            → RIDER_ASSIGNED

        Assignment:
            → ASSIGNED
        """

        delivery = cls._lock_delivery(
            delivery,
        )

        cls._ensure_not_assigned(
            delivery,
        )

        rider = cls._lock_rider(
            rider,
        )

        cls._ensure_rider_assignable(
            rider,
        )

        assignment = DeliveryAssignment.objects.create(
            delivery=delivery,
            rider=rider,
            assigned_by=assigned_by,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .ASSIGNED
            ),
        )

        # ----------------------------------------------
        # Rider → unavailable
        # ----------------------------------------------

        cls._set_rider_availability(
            rider,
            False,
        )

        # ----------------------------------------------
        # Delivery → Rider Assigned
        # ----------------------------------------------

        cls._update_delivery_status(
            delivery,
            Delivery.DeliveryStatus.RIDER_ASSIGNED,
        )

        # ----------------------------------------------
        # Cancel competing offers
        # ----------------------------------------------

        cls._cancel_pending_offers(
            delivery=delivery,
            accepted_rider=rider,
        )

        # ----------------------------------------------
        # Notifications
        # ----------------------------------------------

        cls._schedule_assignment_notifications(
            assignment,
        )

        return assignment

    # ==================================================
    # Accept
    # ==================================================

    @classmethod
    @transaction.atomic
    def accept(
        cls,
        assignment,
    ):
        """
        Rider accepts an assigned delivery.

        Assignment:
            ASSIGNED → ACCEPTED

        Delivery:
            RIDER_ASSIGNED → RIDER_ACCEPTED
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ASSIGNED,
        )

        assignment = cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ACCEPTED,
            accepted_at=timezone.now(),
        )

        cls._update_delivery_status(
            assignment.delivery,
            Delivery.DeliveryStatus.RIDER_ACCEPTED,
        )

        return assignment

    # ==================================================
    # Start Pickup
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_pickup(
        cls,
        assignment,
    ):
        """
        Rider starts travelling toward pickup.

        Assignment:
            ACCEPTED → EN_ROUTE_PICKUP

        Delivery remains:
            RIDER_ACCEPTED
        """

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
    # Arrive Pickup
    # ==================================================

    @classmethod
    @transaction.atomic
    def arrive_pickup(
        cls,
        assignment,
    ):
        """
        Rider arrives at the pickup location.

        Assignment:
            EN_ROUTE_PICKUP → ARRIVED_PICKUP

        Delivery remains:
            RIDER_ACCEPTED
        """

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
    # Pickup Completed
    # ==================================================

    @classmethod
    @transaction.atomic
    def pickup_completed(
        cls,
        assignment,
    ):
        """
        Package has been collected.

        Assignment:
            ARRIVED_PICKUP → PICKED_UP

        Delivery:
            RIDER_ACCEPTED → PICKED_UP
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
        )

        assignment = cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.PICKED_UP,
        )

        cls._update_delivery_status(
            assignment.delivery,
            Delivery.DeliveryStatus.PICKED_UP,
        )

        return assignment

    # ==================================================
    # Start Delivery
    # ==================================================

    @classmethod
    @transaction.atomic
    def start_delivery(
        cls,
        assignment,
    ):
        """
        Rider starts travelling to destination.

        Assignment:
            PICKED_UP → OUT_FOR_DELIVERY

        Delivery:
            PICKED_UP → IN_TRANSIT
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.PICKED_UP,
        )

        assignment = cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.OUT_FOR_DELIVERY,
        )

        cls._update_delivery_status(
            assignment.delivery,
            Delivery.DeliveryStatus.IN_TRANSIT,
        )

        return assignment

    # ==================================================
    # Arrive Destination
    # ==================================================

    @classmethod
    @transaction.atomic
    def arrive_destination(
        cls,
        assignment,
    ):
        """
        Rider arrives at destination.

        Assignment:
            OUT_FOR_DELIVERY → ARRIVED_DESTINATION

        Delivery remains:
            IN_TRANSIT
        """

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
    # Complete
    # ==================================================

    @classmethod
    @transaction.atomic
    def complete(
        cls,
        assignment,
    ):
        """
        Complete the delivery.

        Assignment:
            ARRIVED_DESTINATION → COMPLETED

        Delivery:
            IN_TRANSIT → DELIVERED
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ARRIVED_DESTINATION,
        )

        assignment = cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.COMPLETED,
            completed_at=timezone.now(),
            is_active=False,
        )

        cls._update_delivery_status(
            assignment.delivery,
            Delivery.DeliveryStatus.DELIVERED,
        )

        # ----------------------------------------------
        # Rider can receive another delivery
        # ----------------------------------------------

        cls._set_rider_availability_if_free(
            assignment.rider,
        )

        return assignment

    # ==================================================
    # Cancel
    # ==================================================

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        assignment,
        reason="",
    ):
        """
        Cancel an active assignment.

        The delivery itself is not automatically
        cancelled because it may be redispatched.
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_cancellable(
            assignment,
        )

        assignment = cls._update_assignment_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.CANCELLED,
            cancelled_at=timezone.now(),
            cancellation_reason=reason,
            is_active=False,
        )

        cls._set_rider_availability_if_free(
            assignment.rider,
        )

        return assignment

    # ==================================================
    # Reassign
    # ==================================================

    @classmethod
    @transaction.atomic
    def reassign(
        cls,
        assignment,
    ):
        """
        Validate that the cancelled assignment is ready
        for redispatch.

        This method does not create the new assignment.
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_reassignable(
            assignment,
        )

        return assignment

    # ==================================================
    # Lock Delivery
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

    # ==================================================
    # Lock Assignment
    # ==================================================

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

    # ==================================================
    # Lock Rider
    # ==================================================

    @staticmethod
    def _lock_rider(
        rider,
    ):
        """
        Lock the rider's profile before checking and
        changing availability.
        """

        from riders.models import RiderProfile

        profile = (
            RiderProfile.objects
            .select_for_update()
            .select_related("user")
            .get(
                user=rider,
            )
        )

        return profile.user

    # ==================================================
    # Assignment Validation
    # ==================================================

    @classmethod
    def _ensure_not_assigned(
        cls,
        delivery,
    ):
        exists = (
            DeliveryAssignment.objects
            .filter(
                delivery=delivery,
                status__in=cls.ACTIVE_ASSIGNMENT_STATUSES,
                is_active=True,
            )
            .exists()
        )

        if exists:
            raise AssignmentAlreadyExists(
                "Delivery already has an active "
                "rider assignment."
            )

    # ==================================================
    # Rider Validation
    # ==================================================

    @classmethod
    def _ensure_rider_assignable(
        cls,
        rider,
    ):
        profile = getattr(
            rider,
            "rider_profile",
            None,
        )

        if profile is None:
            raise InvalidAssignmentState(
                "Rider does not have a rider profile."
            )

        if not rider.is_active:
            raise InvalidAssignmentState(
                "Rider account is not active."
            )

        if not rider.is_verified:
            raise InvalidAssignmentState(
                "Rider is not verified."
            )

        if not profile.is_online:
            raise InvalidAssignmentState(
                "Rider is offline."
            )

        if not profile.is_available:
            raise InvalidAssignmentState(
                "Rider is currently unavailable."
            )

        if (
            profile.verification_status
            != RiderProfile.VerificationStatus.APPROVED
        ):
            raise InvalidAssignmentState(
                "Rider verification is not approved."
            )

        has_active_assignment = (
            DeliveryAssignment.objects
            .filter(
                rider=rider,
                status__in=cls.ACTIVE_ASSIGNMENT_STATUSES,
                is_active=True,
            )
            .exists()
        )

        if has_active_assignment:
            raise InvalidAssignmentState(
                "Rider already has an active assignment."
            )

    # ==================================================
    # Status Validation
    # ==================================================

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

    # ==================================================
    # Cancellation Validation
    # ==================================================

    @classmethod
    def _ensure_cancellable(
        cls,
        assignment,
    ):
        if assignment.status not in cls.CANCELLABLE_STATUSES:
            raise InvalidAssignmentState(
                f"Assignment with status "
                f"'{assignment.status}' "
                f"cannot be cancelled."
            )

    # ==================================================
    # Reassignment Validation
    # ==================================================

    @staticmethod
    def _ensure_reassignable(
        assignment,
    ):
        if (
            assignment.status
            != DeliveryAssignment.AssignmentStatus.CANCELLED
        ):
            raise InvalidAssignmentState(
                f"Assignment with status "
                f"'{assignment.status}' "
                f"cannot be reassigned."
            )

    # ==================================================
    # Assignment State Update
    # ==================================================

    @staticmethod
    def _update_assignment_status(
        assignment,
        status,
        **extra_fields,
    ):
        assignment.status = status

        update_fields = [
            "status",
        ]

        for field_name, value in extra_fields.items():

            setattr(
                assignment,
                field_name,
                value,
            )

            update_fields.append(
                field_name,
            )

        assignment.save(
            update_fields=update_fields,
        )

        return assignment

    # ==================================================
    # Delivery State Update
    # ==================================================

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

    # ==================================================
    # Rider Availability
    # ==================================================

    @staticmethod
    def _set_rider_availability(
        rider,
        available,
    ):
        from riders.models import RiderProfile

        RiderProfile.objects.filter(
            user=rider,
        ).update(
            is_available=available,
        )

    # ==================================================
    # Rider Availability If Free
    # ==================================================

    @classmethod
    def _set_rider_availability_if_free(
        cls,
        rider,
    ):
        """
        Make the rider available only when they no
        longer have another active assignment.
        """

        has_active_assignment = (
            DeliveryAssignment.objects
            .filter(
                rider=rider,
                status__in=cls.ACTIVE_ASSIGNMENT_STATUSES,
                is_active=True,
            )
            .exists()
        )

        if not has_active_assignment:
            cls._set_rider_availability(
                rider,
                True,
            )

    # ==================================================
    # Cancel Competing Offers
    # ==================================================

    @staticmethod
    def _cancel_pending_offers(
        delivery,
        accepted_rider,
    ):
        (
            DeliveryOffer.objects
            .filter(
                delivery=delivery,
                status=DeliveryOffer.Status.PENDING,
            )
            .exclude(
                rider=accepted_rider,
            )
            .update(
                status=DeliveryOffer.Status.CANCELLED,
                responded_at=timezone.now(),
            )
        )

    # ==================================================
    # Notifications
    # ==================================================

    @staticmethod
    def _schedule_assignment_notifications(
        assignment,
    ):
        from .notifier import DispatchNotifier

        transaction.on_commit(
            lambda: (
                DispatchNotifier.notify_rider(
                    assignment,
                ),
                DispatchNotifier.notify_customer(
                    assignment,
                ),
                DispatchNotifier.notify_vendor(
                    assignment,
                ),
            )
        )
    

