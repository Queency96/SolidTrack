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

    Concurrency
    -----------
    Assignment operations lock the relevant delivery,
    assignment, and rider profile rows before changing
    state.

    The RiderProfile row is the synchronization point
    for rider availability.
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

    # Cancellation is intentionally restricted to the
    # pre-pickup portion of the assignment lifecycle.
    CANCELLABLE_STATUSES = (
        DeliveryAssignment.AssignmentStatus.ASSIGNED,
        DeliveryAssignment.AssignmentStatus.ACCEPTED,
        DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
        DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
    )

    # A delivery can receive a new assignment only
    # while waiting to be dispatched.
    ASSIGNABLE_DELIVERY_STATUSES = (
        Delivery.DeliveryStatus.PENDING,
        Delivery.DeliveryStatus.WAITING_FOR_RIDER,
    )

    TERMINAL_DELIVERY_STATUSES = (
        Delivery.DeliveryStatus.DELIVERED,
        Delivery.DeliveryStatus.CANCELLED,
        Delivery.DeliveryStatus.FAILED,
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
            PENDING / WAITING_FOR_RIDER
                ↓
            RIDER_ASSIGNED

        Assignment:
            → ASSIGNED

        The delivery and rider profile are locked before
        validation so that two concurrent dispatch
        operations cannot assign the same rider/delivery.
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

        # ----------------------------------------------
        # Lock rider/profile
        # ----------------------------------------------

        rider, rider_profile = cls._lock_rider(
            rider,
        )

        # ----------------------------------------------
        # Validate rider
        # ----------------------------------------------

        cls._ensure_rider_assignable(
            rider=rider,
            profile=rider_profile,
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
            profile=rider_profile,
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

        # ----------------------------------------------
        # Validate assignment
        # ----------------------------------------------

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ASSIGNED,
        )

        cls._ensure_assignment_active(
            assignment,
        )

        # ----------------------------------------------
        # Lock delivery
        # ----------------------------------------------

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        # ----------------------------------------------
        # Validate delivery state
        # ----------------------------------------------

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.RIDER_ASSIGNED,
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
        # Delivery → rider accepted
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

        Delivery:
            remains RIDER_ACCEPTED
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ACCEPTED,
        )

        cls._ensure_assignment_active(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.RIDER_ACCEPTED,
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

        Delivery:
            remains RIDER_ACCEPTED
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

        cls._ensure_assignment_active(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.RIDER_ACCEPTED,
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

        cls._ensure_assignment_active(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.RIDER_ACCEPTED,
        )

        # ----------------------------------------------
        # Assignment → picked up
        # ----------------------------------------------

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .PICKED_UP
            ),
        )

        # ----------------------------------------------
        # Delivery → picked up
        # ----------------------------------------------

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

        cls._ensure_assignment_active(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.PICKED_UP,
        )

        # ----------------------------------------------
        # Assignment → out for delivery
        # ----------------------------------------------

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .OUT_FOR_DELIVERY
            ),
        )

        # ----------------------------------------------
        # Delivery → in transit
        # ----------------------------------------------

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

        Delivery:
            remains IN_TRANSIT
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

        cls._ensure_assignment_active(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.IN_TRANSIT,
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

        cls._ensure_assignment_active(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.IN_TRANSIT,
        )

        now = timezone.now()

        # ----------------------------------------------
        # Assignment → completed
        # ----------------------------------------------

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .COMPLETED
            ),
            completed_at=now,
            is_active=False,
        )

        # ----------------------------------------------
        # Delivery → delivered
        # ----------------------------------------------

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .DELIVERED
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
        Cancel an active assignment before pickup.

        Assignment:
            active → CANCELLED

        Delivery:
            → WAITING_FOR_RIDER

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

        now = timezone.now()

        # ----------------------------------------------
        # Assignment → cancelled
        # ----------------------------------------------

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .CANCELLED
            ),
            cancelled_at=now,
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
        Validate that a cancelled assignment can be
        handed back to the dispatch system.

        This method does not create a new assignment.

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

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.WAITING_FOR_RIDER,
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

        The delivery row is the synchronization point
        for assignment operations involving the same
        delivery.
        """

        if delivery is None:
            raise InvalidAssignmentState(
                "Delivery is required."
            )

        delivery_id = getattr(
            delivery,
            "pk",
            delivery,
        )

        try:
            return (
                Delivery.objects
                .select_for_update()
                .get(
                    pk=delivery_id,
                )
            )

        except Delivery.DoesNotExist:
            raise InvalidAssignmentState(
                "Delivery does not exist."
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

        assignment_id = getattr(
            assignment,
            "pk",
            assignment,
        )

        try:
            return (
                DeliveryAssignment.objects
                .select_for_update()
                .select_related(
                    "delivery",
                    "rider",
                )
                .get(
                    pk=assignment_id,
                )
            )

        except DeliveryAssignment.DoesNotExist:
            raise InvalidAssignmentState(
                "Assignment does not exist."
            )

    # ==================================================
    # Lock Rider
    # ==================================================

    @staticmethod
    def _lock_rider(
        rider,
    ):
        """
        Lock the RiderProfile row.

        Returns:
            (rider_user, rider_profile)
        """

        if rider is None:
            raise InvalidAssignmentState(
                "Rider is required."
            )

        rider_id = getattr(
            rider,
            "pk",
            rider,
        )

        try:
            profile = (
                RiderProfile.objects
                .select_for_update()
                .select_related("user")
                .get(
                    user_id=rider_id,
                )
            )

        except RiderProfile.DoesNotExist:
            raise InvalidAssignmentState(
                "Rider does not have a rider profile."
            )

        return profile.user, profile

    # ==================================================
    # Assignment Active Validation
    # ==================================================

    @staticmethod
    def _ensure_assignment_active(
        assignment,
    ):
        """
        Ensure the assignment is still active.
        """

        if not assignment.is_active:
            raise InvalidAssignmentState(
                "Assignment is inactive."
            )

    # ==================================================
    # Delivery Validation
    # ==================================================

    @classmethod
    def _ensure_delivery_not_terminal(
        cls,
        delivery,
    ):
        """
        Ensure the delivery has not reached a terminal
        state.
        """

        if delivery.status in (
            cls.TERMINAL_DELIVERY_STATUSES
        ):
            raise InvalidAssignmentState(
                f"Delivery with status "
                f"'{delivery.status}' is terminal."
            )

    @classmethod
    def _ensure_delivery_assignable(
        cls,
        delivery,
    ):
        """
        Only PENDING and WAITING_FOR_RIDER deliveries
        may receive a new assignment.
        """

        if delivery.status not in (
            cls.ASSIGNABLE_DELIVERY_STATUSES
        ):
            raise InvalidAssignmentState(
                f"Delivery with status "
                f"'{delivery.status}' cannot "
                f"be assigned."
            )

        cls._ensure_not_assigned(
            delivery,
        )

    @staticmethod
    def _ensure_delivery_status(
        delivery,
        expected,
    ):
        """
        Ensure the delivery is in the exact expected
        state for the transition.
        """

        if delivery.status != expected:
            raise InvalidAssignmentState(
                f"Expected delivery status "
                f"'{expected}' but got "
                f"'{delivery.status}'."
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
        profile,
    ):
        """
        Validate rider state immediately before
        assignment.

        The supplied profile has already been locked
        by _lock_rider().
        """

        # ----------------------------------------------
        # Account
        # ----------------------------------------------

        if not rider.is_active:
            raise InvalidAssignmentState(
                "Rider account is not active."
            )

        if not rider.is_verified:
            raise InvalidAssignmentState(
                "Rider is not verified."
            )

        # ----------------------------------------------
        # Role
        # ----------------------------------------------

        rider_role = getattr(
            rider,
            "role",
            None,
        )

        if rider_role != rider.Roles.RIDER:
            raise InvalidAssignmentState(
                "User is not a rider."
            )

        # ----------------------------------------------
        # Profile
        # ----------------------------------------------

        if profile is None:
            raise InvalidAssignmentState(
                "Rider does not have a rider profile."
            )

        # ----------------------------------------------
        # Online
        # ----------------------------------------------

        if not profile.is_online:
            raise InvalidAssignmentState(
                "Rider is offline."
            )

        # ----------------------------------------------
        # Availability
        # ----------------------------------------------

        if not profile.is_available:
            raise InvalidAssignmentState(
                "Rider is currently unavailable."
            )

        # ----------------------------------------------
        # Verification
        # ----------------------------------------------

        if (
            profile.verification_status
            != (
                RiderProfile
                .VerificationStatus
                .APPROVED
            )
        ):
            raise InvalidAssignmentState(
                "Rider verification is not approved."
            )

        # ----------------------------------------------
        # Existing active assignment
        # ----------------------------------------------

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
    # Assignment Status Validation
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

        cls._ensure_assignment_active(
            assignment,
        )

        if assignment.status not in (
            cls.CANCELLABLE_STATUSES
        ):
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

        if assignment.is_active:
            raise InvalidAssignmentState(
                "Cancelled assignment must be inactive."
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

        Only changed fields are persisted.
        """

        assignment.status = status

        update_fields = {
            "status",
        }

        for field_name, value in extra_fields.items():

            setattr(
                assignment,
                field_name,
                value,
            )

            update_fields.add(
                field_name,
            )

        # ----------------------------------------------
        # TimeStampedModel compatibility
        # ----------------------------------------------

        if hasattr(
            assignment,
            "updated_at",
        ):
            update_fields.add(
                "updated_at",
            )

        assignment.save(
            update_fields=list(
                update_fields,
            ),
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
        Update delivery status and automatically
        populate the timestamp associated with that
        status.

        Existing timestamps are not cleared when a
        delivery changes status.
        """

        now = timezone.now()

        timestamp_fields = {
            Delivery.DeliveryStatus.WAITING_FOR_RIDER:
                "waiting_for_rider_at",

            Delivery.DeliveryStatus.RIDER_ASSIGNED:
                "rider_assigned_at",

            Delivery.DeliveryStatus.RIDER_ACCEPTED:
                "rider_accepted_at",

            Delivery.DeliveryStatus.PICKED_UP:
                "picked_up_at",

            Delivery.DeliveryStatus.IN_TRANSIT:
                "in_transit_at",

            Delivery.DeliveryStatus.DELIVERED:
                "delivered_at",

            Delivery.DeliveryStatus.CANCELLED:
                "cancelled_at",

            Delivery.DeliveryStatus.FAILED:
                "failed_at",
        }

        delivery.status = status

        update_fields = {
            "status",
        }

        timestamp_field = timestamp_fields.get(
            status,
        )

        if timestamp_field:

            setattr(
                delivery,
                timestamp_field,
                now,
            )

            update_fields.add(
                timestamp_field,
            )

        # ----------------------------------------------
        # TimeStampedModel compatibility
        # ----------------------------------------------

        if hasattr(
            delivery,
            "updated_at",
        ):
            update_fields.add(
                "updated_at",
            )

        delivery.save(
            update_fields=list(
                update_fields,
            ),
        )

    # ==================================================
    # Rider Availability
    # ==================================================

    @staticmethod
    def _set_rider_availability(
        profile,
        available,
    ):
        """
        Update rider availability.

        The profile MUST already be locked by the
        caller.
        """

        if profile is None:
            raise InvalidAssignmentState(
                "Rider profile does not exist."
            )

        profile.is_available = available

        update_fields = [
            "is_available",
        ]

        if hasattr(
            profile,
            "updated_at",
        ):
            update_fields.append(
                "updated_at",
            )

        profile.save(
            update_fields=update_fields,
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
        Make the rider available only when there are
        no remaining active assignments.

        The RiderProfile row is locked before checking
        the rider's assignment state.
        """

        try:

            profile = (
                RiderProfile.objects
                .select_for_update()
                .get(
                    user=rider,
                )
            )

        except RiderProfile.DoesNotExist:
            raise InvalidAssignmentState(
                "Rider profile does not exist."
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

            update_fields = [
                "is_available",
            ]

            if hasattr(
                profile,
                "updated_at",
            ):
                update_fields.append(
                    "updated_at",
                )

            profile.save(
                update_fields=update_fields,
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
        Cancel all pending offers for the delivery
        except the selected rider's offer.

        This prevents another rider from accepting a
        competing pending offer after assignment.
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
        Schedule notifications only after the database
        transaction commits successfully.

        Notification failures therefore cannot roll back
        the assignment transaction.
        """

        from .notifier import DispatchNotifier

        def notify():
            """
            Execute all assignment notifications.

            Each notification is isolated so that a
            failure in one notification does not prevent
            the remaining notifications from executing.
            """

            notification_methods = (
                DispatchNotifier.notify_rider,
                DispatchNotifier.notify_customer,
                DispatchNotifier.notify_vendor,
            )

            for notify_method in notification_methods:

                try:
                    notify_method(
                        assignment,
                    )

                except Exception:
                    # Notification infrastructure should
                    # never break the dispatch transaction.
                    pass

        transaction.on_commit(
            notify,
        )