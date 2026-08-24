from django.db import transaction
from django.utils import timezone

from deliveries.models.models import (
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

    Concurrency
    -----------
    Assignment operations lock the relevant delivery,
    assignment, and rider profile rows before changing
    state.
    """

    # ==================================================
    # Assignment Status Groups
    # ==================================================

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

        This method performs a final rider validation
        immediately before assignment.
        """

        # ----------------------------------------------
        # Lock delivery
        # ----------------------------------------------

        delivery = cls._lock_delivery(
            delivery,
        )

        # ----------------------------------------------
        # Validate delivery
        # ----------------------------------------------

        cls._ensure_delivery_assignable(
            delivery,
        )

        cls._ensure_not_assigned(
            delivery,
        )

        # ----------------------------------------------
        # Lock rider
        # ----------------------------------------------

        rider = cls._lock_rider(
            rider,
        )

        # ----------------------------------------------
        # Validate rider
        # ----------------------------------------------

        cls._ensure_rider_assignable(
            rider,
        )

        # ----------------------------------------------
        # Create assignment
        # ----------------------------------------------

        assignment = DeliveryAssignment.objects.create(
            delivery=delivery,
            rider=rider,
            assigned_by=assigned_by,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .ASSIGNED
            ),
            is_active=True,
        )

        # ----------------------------------------------
        # Rider → unavailable
        # ----------------------------------------------

        cls._set_rider_availability(
            rider=rider,
            available=False,
        )

        # ----------------------------------------------
        # Delivery → rider assigned
        # ----------------------------------------------

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .RIDER_ASSIGNED
            ),
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

        # ----------------------------------------------
        # Lock delivery
        # ----------------------------------------------

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        # ----------------------------------------------
        # Validate delivery
        # ----------------------------------------------

        cls._ensure_delivery_not_terminal(
            delivery,
        )

        # ----------------------------------------------
        # Update assignment
        # ----------------------------------------------

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .ACCEPTED
            ),
            accepted_at=timezone.now(),
        )

        # ----------------------------------------------
        # Update delivery
        # ----------------------------------------------

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .RIDER_ACCEPTED
            ),
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

        cls._ensure_delivery_not_terminal(
            assignment.delivery,
        )

        return cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .EN_ROUTE_PICKUP
            ),
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
        Rider arrives at pickup.

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
            (
                DeliveryAssignment
                .AssignmentStatus
                .EN_ROUTE_PICKUP
            ),
        )

        cls._ensure_delivery_not_terminal(
            assignment.delivery,
        )

        return cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .ARRIVED_PICKUP
            ),
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
            (
                DeliveryAssignment
                .AssignmentStatus
                .ARRIVED_PICKUP
            ),
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_not_terminal(
            delivery,
        )

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .PICKED_UP
            ),
        )

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .PICKED_UP
            ),
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
            (
                DeliveryAssignment
                .AssignmentStatus
                .PICKED_UP
            ),
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_not_terminal(
            delivery,
        )

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .OUT_FOR_DELIVERY
            ),
        )

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .IN_TRANSIT
            ),
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
            (
                DeliveryAssignment
                .AssignmentStatus
                .OUT_FOR_DELIVERY
            ),
        )

        cls._ensure_delivery_not_terminal(
            assignment.delivery,
        )

        return cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .ARRIVED_DESTINATION
            ),
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
            (
                DeliveryAssignment
                .AssignmentStatus
                .ARRIVED_DESTINATION
            ),
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_not_terminal(
            delivery,
        )

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .COMPLETED
            ),
            completed_at=timezone.now(),
            is_active=False,
        )

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .DELIVERED
            ),
        )

        # ----------------------------------------------
        # Rider → available if no other active job
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

        The assignment becomes inactive.

        The delivery is moved back to
        WAITING_FOR_RIDER so DispatchCoordinator
        can redispatch it.

        The delivery itself is NOT cancelled.
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_cancellable(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_not_terminal(
            delivery,
        )

        # ----------------------------------------------
        # Cancel assignment
        # ----------------------------------------------

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .CANCELLED
            ),
            cancelled_at=timezone.now(),
            cancellation_reason=reason,
            is_active=False,
        )

        # ----------------------------------------------
        # Delivery → waiting for rider
        # ----------------------------------------------

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .WAITING_FOR_RIDER
            ),
        )

        # ----------------------------------------------
        # Rider → available if free
        # ----------------------------------------------

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
        Validate that a cancelled assignment is ready
        for redispatch.

        This method does not create the new assignment.

        DispatchCoordinator is responsible for starting
        the new dispatch lifecycle.
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_reassignable(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_not_terminal(
            delivery,
        )

        return assignment

    # ==================================================
    # Lock Delivery
    # ==================================================

    @staticmethod
    def _lock_delivery(
        delivery,
    ):
        """
        Lock the delivery row.

        Prevents concurrent assignment operations
        against the same delivery.
        """

        if delivery is None:
            raise InvalidAssignmentState(
                "Delivery is required."
            )

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
        """
        Lock the assignment row before changing state.
        """

        if assignment is None:
            raise InvalidAssignmentState(
                "Assignment is required."
            )

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
        Lock the rider profile before checking or
        changing rider availability.

        The RiderProfile row is the synchronization
        point for rider availability.
        """

        if rider is None:
            raise InvalidAssignmentState(
                "Rider is required."
            )

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
    # Delivery Validation
    # ==================================================

    @staticmethod
    def _ensure_delivery_not_terminal(
        delivery,
    ):
        """
        Ensure the delivery has not reached a terminal
        state.
        """

        terminal_statuses = {
            Delivery.DeliveryStatus.DELIVERED,
            Delivery.DeliveryStatus.CANCELLED,
        }

        if delivery.status in terminal_statuses:

            raise InvalidAssignmentState(
                f"Delivery with status "
                f"'{delivery.status}' is terminal."
            )

    # ==================================================
    # Delivery Assignment Validation
    # ==================================================

    @classmethod
    def _ensure_delivery_assignable(
        cls,
        delivery,
    ):
        """
        Ensure the delivery can receive a rider
        assignment.
        """

        cls._ensure_delivery_not_terminal(
            delivery,
        )

        # ------------------------------------------
        # Existing active assignment
        # ------------------------------------------

        cls._ensure_not_assigned(
            delivery,
        )

    # ==================================================
    # Assignment Validation
    # ==================================================

    @classmethod
    def _ensure_not_assigned(
        cls,
        delivery,
    ):
        """
        Ensure the delivery has no active assignment.
        """

        exists = (
            DeliveryAssignment.objects
            .filter(
                delivery=delivery,
                status__in=(
                    cls.ACTIVE_ASSIGNMENT_STATUSES
                ),
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
        """
        Validate rider state immediately before
        assignment.
        """

        # ------------------------------------------
        # Account
        # ------------------------------------------

        if not rider.is_active:

            raise InvalidAssignmentState(
                "Rider account is not active."
            )

        if not rider.is_verified:

            raise InvalidAssignmentState(
                "Rider is not verified."
            )

        # ------------------------------------------
        # Rider role
        # ------------------------------------------

        rider_role = getattr(
            rider,
            "role",
            None,
        )

        if rider_role != rider.Roles.RIDER:

            raise InvalidAssignmentState(
                "User is not a rider."
            )

        # ------------------------------------------
        # Profile
        # ------------------------------------------

        profile = getattr(
            rider,
            "rider_profile",
            None,
        )

        if profile is None:

            raise InvalidAssignmentState(
                "Rider does not have a rider profile."
            )

        # ------------------------------------------
        # Online
        # ------------------------------------------

        if not profile.is_online:

            raise InvalidAssignmentState(
                "Rider is offline."
            )

        # ------------------------------------------
        # Availability
        # ------------------------------------------

        if not profile.is_available:

            raise InvalidAssignmentState(
                "Rider is currently unavailable."
            )

        # ------------------------------------------
        # Verification
        # ------------------------------------------

        if (
            profile.verification_status
            != RiderProfile
            .VerificationStatus
            .APPROVED
        ):

            raise InvalidAssignmentState(
                "Rider verification is not approved."
            )

        # ------------------------------------------
        # Existing active assignment
        # ------------------------------------------

        has_active_assignment = (
            DeliveryAssignment.objects
            .filter(
                rider=rider,
                status__in=(
                    cls.ACTIVE_ASSIGNMENT_STATUSES
                ),
                is_active=True,
            )
            .exists()
        )

        if has_active_assignment:

            raise InvalidAssignmentState(
                "Rider already has an active "
                "assignment."
            )

    # ==================================================
    # Status Validation
    # ==================================================

    @staticmethod
    def _ensure_status(
        assignment,
        expected,
    ):
        """
        Ensure the assignment is currently in the
        expected state.
        """

        if assignment.status != expected:

            raise InvalidAssignmentState(
                f"Expected assignment status "
                f"'{expected}' but got "
                f"'{assignment.status}'."
            )

    # ==================================================
    # Cancellation Validation
    # ==================================================

    @classmethod
    def _ensure_cancellable(
        cls,
        assignment,
    ):
        """
        Ensure the assignment can be cancelled.
        """

        if assignment.status not in (
            cls.CANCELLABLE_STATUSES
        ):

            raise InvalidAssignmentState(
                f"Assignment with status "
                f"'{assignment.status}' "
                f"cannot be cancelled."
            )

        if not assignment.is_active:

            raise InvalidAssignmentState(
                "Assignment is already inactive."
            )

    # ==================================================
    # Reassignment Validation
    # ==================================================

    @staticmethod
    def _ensure_reassignable(
        assignment,
    ):
        """
        Ensure the assignment has been cancelled
        before redispatch.
        """

        if (
            assignment.status
            != (
                DeliveryAssignment
                .AssignmentStatus
                .CANCELLED
            )
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
        """
        Update assignment state.
        """

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
        """
        Update delivery status.
        """

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
        """
        Update rider availability.

        The profile row should already be locked by
        the caller whenever this operation occurs
        inside a transaction.
        """

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
        Make the rider available only if there are
        no remaining active assignments.

        The RiderProfile row is locked before the
        availability decision is made.
        """

        profile = (
            RiderProfile.objects
            .select_for_update()
            .get(
                user=rider,
            )
        )

        has_active_assignment = (
            DeliveryAssignment.objects
            .filter(
                rider=rider,
                status__in=(
                    cls.ACTIVE_ASSIGNMENT_STATUSES
                ),
                is_active=True,
            )
            .exists()
        )

        if not has_active_assignment:

            profile.is_available = True

            profile.save(
                update_fields=[
                    "is_available",
                ],
            )

    # ==================================================
    # Cancel Competing Offers
    # ==================================================

    @staticmethod
    def _cancel_pending_offers(
        delivery,
        accepted_rider,
    ):
        """
        Cancel every pending offer for the delivery
        except the offer belonging to the accepted rider.

        This prevents other riders from accepting an
        offer after the delivery has already been assigned.
        """

        (
            DeliveryOffer.objects
            .filter(
                delivery=delivery,
                status=(
                    DeliveryOffer.Status.PENDING
                ),
            )
            .exclude(
                rider=accepted_rider,
            )
            .update(
                status=(
                    DeliveryOffer.Status.CANCELLED
                ),
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
        """
        Schedule assignment notifications only after
        the database transaction successfully commits.

        Notification failures therefore cannot cause
        the assignment transaction to roll back.
        """

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