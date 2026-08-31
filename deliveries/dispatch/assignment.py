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
from .service import DispatchConfigurationService


class AssignmentService:
    """
    Handles the lifecycle of DeliveryAssignment.

    ============================================================
    CORE BUSINESS RULE
    ============================================================

    A delivery has EXACTLY ONE lifetime assignment record.

    Example:

        Delivery #100

            Assignment #1
                Rider A
                ↓
                CANCELLED
                ↓
                restarted by admin
                ↓
                Rider B
                ↓
                ASSIGNED
                ↓
                COMPLETED

    Assignment #2 is NEVER created.

    The same DeliveryAssignment database row is reused when an
    administrator explicitly restarts a previously cancelled
    assignment.

    ============================================================
    BUSINESS RULES
    ============================================================

    1. A delivery may have a maximum of ONE
       DeliveryAssignment record for its entire lifetime.

    2. max_rider_assignments = 1.

    3. DeliveryOffer and DeliveryAssignment are different.

       DeliveryOffer:
           Temporary invitation to a rider.

       DeliveryAssignment:
           The single lifetime assignment record.

    4. Rider may:

           - Accept a DeliveryOffer
           - Reject a DeliveryOffer
           - Allow a DeliveryOffer to expire
           - Cancel a pending DeliveryOffer

    5. Rider may NOT cancel a DeliveryAssignment.

    6. Admin/staff may cancel an assignment according to the
       cancellation rules.

    7. Cancelling an assignment does NOT create a new assignment
       slot.

    8. A cancelled assignment remains the SAME assignment row.

    9. Admin/staff may explicitly restart a cancelled assignment.

    10. Restarting does NOT create a new DeliveryAssignment.

    11. After restart:

            Delivery
                ↓
            WAITING_FOR_RIDER
                ↓
            new DeliveryOffer
                ↓
            rider accepts
                ↓
            existing Assignment #1 is reused

    12. No second DeliveryAssignment row can ever exist.

    ============================================================
    CONCURRENCY
    ============================================================

    Delivery is the synchronization point for assignment
    creation/reuse.

        SELECT FOR UPDATE delivery
                    ↓
        inspect existing assignment
                    ↓
        create OR reuse Assignment #1
                    ↓
        update rider
                    ↓
        update delivery

    Therefore concurrent assignment attempts for the same
    delivery are serialized.
    """

    # ============================================================
    # ASSIGNMENT STATUS GROUPS
    # ============================================================

    ACTIVE_ASSIGNMENT_STATUSES = (
        DeliveryAssignment.AssignmentStatus.ASSIGNED,
        DeliveryAssignment.AssignmentStatus.ACCEPTED,
        DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
        DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
        DeliveryAssignment.AssignmentStatus.PICKED_UP,
        DeliveryAssignment.AssignmentStatus.OUT_FOR_DELIVERY,
        DeliveryAssignment.AssignmentStatus.ARRIVED_DESTINATION,
    )

    # ------------------------------------------------------------
    # ADMIN CANCELLABLE STATES
    # ------------------------------------------------------------

    ADMIN_CANCELLABLE_STATUSES = (
        DeliveryAssignment.AssignmentStatus.ASSIGNED,
        DeliveryAssignment.AssignmentStatus.ACCEPTED,
        DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
        DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
    )

    # ------------------------------------------------------------
    # Delivery states that may receive an assignment.
    # ------------------------------------------------------------

    ASSIGNABLE_DELIVERY_STATUSES = (
        Delivery.DeliveryStatus.PENDING,
        Delivery.DeliveryStatus.WAITING_FOR_RIDER,
    )

    # ------------------------------------------------------------
    # Terminal delivery states.
    # ------------------------------------------------------------

    TERMINAL_DELIVERY_STATUSES = (
        Delivery.DeliveryStatus.DELIVERED,
        Delivery.DeliveryStatus.CANCELLED,
        Delivery.DeliveryStatus.FAILED,
    )

    # ============================================================
    # ASSIGN
    # ============================================================

    @classmethod
    @transaction.atomic
    def assign(
        cls,
        delivery,
        rider,
        assigned_by=None,
    ):
        """
        Create OR reuse the single lifetime assignment.

        FIRST DISPATCH
        --------------

        If no DeliveryAssignment exists:

            create Assignment #1

        RESTARTED DISPATCH
        ------------------

        If Assignment #1 exists but is CANCELLED and the delivery
        was explicitly restarted by admin/staff:

            reuse Assignment #1

        NEVER:

            create Assignment #2
        """

        # --------------------------------------------------------
        # Lock delivery
        # --------------------------------------------------------

        delivery = cls._lock_delivery(
            delivery,
        )

        # --------------------------------------------------------
        # Validate delivery
        # --------------------------------------------------------

        cls._ensure_delivery_assignable(
            delivery,
        )

        # --------------------------------------------------------
        # Configuration
        # --------------------------------------------------------

        config = (
            DispatchConfigurationService
            .get_configuration()
        )

        if config is None:
            raise InvalidAssignmentState(
                "No active dispatch configuration "
                "is available."
            )

        # --------------------------------------------------------
        # Lifetime assignment limit
        # --------------------------------------------------------

        maximum = (
            cls._get_maximum_rider_assignments(
                config,
            )
        )

        # --------------------------------------------------------
        # Existing lifetime assignment
        # --------------------------------------------------------

        existing_assignment = (
            DeliveryAssignment.objects
            .select_for_update()
            .filter(
                delivery=delivery,
            )
            .first()
        )

        # --------------------------------------------------------
        # No assignment yet
        # --------------------------------------------------------

        if existing_assignment is None:

            if maximum > 0:

                assignment_count = (
                    cls._get_assignment_count(
                        delivery,
                    )
                )

                if assignment_count >= maximum:

                    raise InvalidAssignmentState(
                        "Maximum rider assignment limit "
                        "has been reached for this delivery."
                    )

            assignment = None

        # --------------------------------------------------------
        # Existing assignment
        # --------------------------------------------------------

        else:

            # ----------------------------------------------------
            # Active assignment already exists.
            # ----------------------------------------------------

            if (
                existing_assignment.status
                in cls.ACTIVE_ASSIGNMENT_STATUSES
                and existing_assignment.is_active
            ):
                raise AssignmentAlreadyExists(
                    "Delivery already has an active "
                    "rider assignment."
                )

            # ----------------------------------------------------
            # Completed assignment can NEVER be reused.
            # ----------------------------------------------------

            if (
                existing_assignment.status
                == DeliveryAssignment.AssignmentStatus.COMPLETED
            ):
                raise AssignmentAlreadyExists(
                    "Delivery assignment has already "
                    "been completed and cannot be reused."
                )

            # ----------------------------------------------------
            # Only CANCELLED assignment may be reused.
            # ----------------------------------------------------

            if (
                existing_assignment.status
                != DeliveryAssignment.AssignmentStatus.CANCELLED
            ):
                raise AssignmentAlreadyExists(
                    "Delivery already has a rider assignment. "
                    "A second assignment is not permitted."
                )

            # ----------------------------------------------------
            # Delivery must have been explicitly reopened.
            #
            # WAITING_FOR_RIDER is the dispatch-ready state.
            # ----------------------------------------------------

            if (
                delivery.status
                != Delivery.DeliveryStatus.WAITING_FOR_RIDER
            ):
                raise InvalidAssignmentState(
                    "The cancelled assignment has not been "
                    "restarted by admin/staff."
                )

            assignment = existing_assignment

        # --------------------------------------------------------
        # Lock rider
        # --------------------------------------------------------

        rider, rider_profile = cls._lock_rider(
            rider,
        )

        # --------------------------------------------------------
        # Validate rider
        # --------------------------------------------------------

        cls._ensure_rider_assignable(
            rider=rider,
            profile=rider_profile,
            exclude_assignment=assignment,
        )

        # --------------------------------------------------------
        # CREATE FIRST ASSIGNMENT
        # --------------------------------------------------------

        if assignment is None:

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

        # --------------------------------------------------------
        # REUSE CANCELLED ASSIGNMENT
        # --------------------------------------------------------

        else:

            assignment.rider = rider
            assignment.assigned_by = assigned_by

            assignment.status = (
                DeliveryAssignment
                .AssignmentStatus
                .ASSIGNED
            )

            assignment.is_active = True

            # ----------------------------------------------------
            # Clear fields belonging to the previous active
            # lifecycle.
            # ----------------------------------------------------

            if hasattr(
                assignment,
                "accepted_at",
            ):
                assignment.accepted_at = None

            if hasattr(
                assignment,
                "completed_at",
            ):
                assignment.completed_at = None

            # ----------------------------------------------------
            # IMPORTANT:
            #
            # We intentionally do NOT clear cancelled_at or
            # cancellation_reason if those fields are intended
            # as audit information.
            #
            # The current assignment lifecycle is ASSIGNED,
            # while the cancellation timestamp remains historical.
            # ----------------------------------------------------

            update_fields = [
                "rider",
                "assigned_by",
                "status",
                "is_active",
            ]

            if hasattr(
                assignment,
                "accepted_at",
            ):
                update_fields.append(
                    "accepted_at",
                )

            if hasattr(
                assignment,
                "completed_at",
            ):
                update_fields.append(
                    "completed_at",
                )

            if hasattr(
                assignment,
                "updated_at",
            ):
                update_fields.append(
                    "updated_at",
                )

            assignment.save(
                update_fields=update_fields,
            )

        # --------------------------------------------------------
        # Rider becomes unavailable.
        # --------------------------------------------------------

        cls._set_rider_availability(
            profile=rider_profile,
            available=False,
        )

        # --------------------------------------------------------
        # Delivery becomes assigned.
        # --------------------------------------------------------

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus.RIDER_ASSIGNED
            ),
        )

        # --------------------------------------------------------
        # Cancel competing offers.
        # --------------------------------------------------------

        cls._cancel_pending_offers(
            delivery=delivery,
            accepted_rider=rider,
        )

        # --------------------------------------------------------
        # Notifications.
        # --------------------------------------------------------

        cls._schedule_assignment_notifications(
            assignment,
        )

        return assignment

    # ============================================================
    # ADMIN / STAFF RESTART CANCELLED ASSIGNMENT
    # ============================================================

    @classmethod
    @transaction.atomic
    def restart_cancelled_assignment(
        cls,
        assignment,
        restarted_by,
    ):
        """
        Explicitly restart the existing Assignment #1.

        This DOES NOT create a new DeliveryAssignment.

        Example:

            Assignment #1
                CANCELLED
                    ↓
                admin restart
                    ↓
                WAITING_FOR_RIDER
                    ↓
                new rider offer

        The assignment remains cancelled until a rider actually
        accepts a new DeliveryOffer.

        This is important because restarting the delivery should
        NOT automatically assign a rider.

        It only makes the delivery eligible for dispatch again.
        """

        # --------------------------------------------------------
        # Validate administrator/staff.
        # --------------------------------------------------------

        cls._ensure_admin_or_staff(
            restarted_by,
        )

        # --------------------------------------------------------
        # Lock assignment.
        # --------------------------------------------------------

        assignment = cls._lock_assignment(
            assignment,
        )

        # --------------------------------------------------------
        # Assignment must be cancelled.
        # --------------------------------------------------------

        if (
            assignment.status
            != DeliveryAssignment.AssignmentStatus.CANCELLED
        ):
            raise InvalidAssignmentState(
                "Only a cancelled assignment can be restarted."
            )

        # --------------------------------------------------------
        # Lock delivery.
        # --------------------------------------------------------

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        # --------------------------------------------------------
        # Delivery cannot be terminal.
        # --------------------------------------------------------

        if delivery.status in (
            Delivery.DeliveryStatus.DELIVERED,
            Delivery.DeliveryStatus.FAILED,
        ):
            raise InvalidAssignmentState(
                f"Delivery with status "
                f"'{delivery.status}' cannot be restarted."
            )

        # --------------------------------------------------------
        # Cancel any stale pending offers.
        # --------------------------------------------------------

        cls._cancel_all_pending_offers(
            delivery=delivery,
        )

        # --------------------------------------------------------
        # Delivery becomes ready for dispatch.
        # --------------------------------------------------------

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .WAITING_FOR_RIDER
            ),
        )

        # --------------------------------------------------------
        # Assignment itself remains CANCELLED until a rider
        # accepts a new offer.
        # --------------------------------------------------------

        return assignment

    # ============================================================
    # ACCEPT ASSIGNMENT
    # ============================================================

    @classmethod
    @transaction.atomic
    def accept(
        cls,
        assignment,
    ):
        """
        Move:

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

        cls._ensure_assignment_active(
            assignment,
        )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.RIDER_ASSIGNED,
        )

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .ACCEPTED
            ),
            accepted_at=timezone.now(),
        )

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .RIDER_ACCEPTED
            ),
        )

        return assignment

    # ============================================================
    # START PICKUP
    # ============================================================

    @classmethod
    @transaction.atomic
    def start_pickup(
        cls,
        assignment,
    ):
        """
        ACCEPTED → EN_ROUTE_PICKUP
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

    # ============================================================
    # ARRIVE PICKUP
    # ============================================================

    @classmethod
    @transaction.atomic
    def arrive_pickup(
        cls,
        assignment,
    ):
        """
        EN_ROUTE_PICKUP → ARRIVED_PICKUP
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
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

    # ============================================================
    # PICKUP COMPLETED
    # ============================================================

    @classmethod
    @transaction.atomic
    def pickup_completed(
        cls,
        assignment,
    ):
        """
        ARRIVED_PICKUP → PICKED_UP
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
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
                Delivery.DeliveryStatus.PICKED_UP
            ),
        )

        return assignment

    # ============================================================
    # START DELIVERY
    # ============================================================

    @classmethod
    @transaction.atomic
    def start_delivery(
        cls,
        assignment,
    ):
        """
        PICKED_UP → OUT_FOR_DELIVERY
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.PICKED_UP,
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
                Delivery.DeliveryStatus.IN_TRANSIT
            ),
        )

        return assignment

    # ============================================================
    # ARRIVE DESTINATION
    # ============================================================

    @classmethod
    @transaction.atomic
    def arrive_destination(
        cls,
        assignment,
    ):
        """
        OUT_FOR_DELIVERY → ARRIVED_DESTINATION
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.OUT_FOR_DELIVERY,
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

    # ============================================================
    # COMPLETE
    # ============================================================

    @classmethod
    @transaction.atomic
    def complete(
        cls,
        assignment,
    ):
        """
        ARRIVED_DESTINATION → COMPLETED

        Once completed, the lifetime assignment is permanently
        consumed and cannot be restarted.
        """

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment.AssignmentStatus.ARRIVED_DESTINATION,
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

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus.DELIVERED
            ),
        )

        cls._set_rider_availability_if_free(
            assignment.rider,
        )

        return assignment

    # ============================================================
    # ADMIN / STAFF CANCEL
    # ============================================================

    @classmethod
    @transaction.atomic
    def cancel_by_admin(
        cls,
        assignment,
        cancelled_by,
        reason="",
    ):
        """
        Cancel the current assignment lifecycle.

        IMPORTANT:

        This does NOT create another assignment slot.

        The same Assignment #1 may later be restarted by
        admin/staff.

            Assignment #1
                ASSIGNED
                    ↓
                CANCELLED
                    ↓
                admin restart
                    ↓
                ASSIGNED
        """

        cls._ensure_admin_or_staff(
            cancelled_by,
        )

        assignment = cls._lock_assignment(
            assignment,
        )

        cls._ensure_assignment_active(
            assignment,
        )

        if assignment.status not in (
            cls.ADMIN_CANCELLABLE_STATUSES
        ):
            raise InvalidAssignmentState(
                f"Assignment with status "
                f"'{assignment.status}' "
                f"cannot be cancelled by admin/staff."
            )

        delivery = cls._lock_delivery(
            assignment.delivery,
        )

        cls._ensure_delivery_not_terminal(
            delivery,
        )

        now = timezone.now()

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

        # --------------------------------------------------------
        # IMPORTANT:
        #
        # We DO NOT create a new assignment.
        #
        # We also do not automatically reopen the delivery.
        #
        # Admin/staff must explicitly call:
        #
        #     restart_cancelled_assignment()
        #
        # when they are ready for dispatch again.
        # --------------------------------------------------------

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus.CANCELLED
            ),
        )

        cls._set_rider_availability_if_free(
            assignment.rider,
        )

        cls._cancel_all_pending_offers(
            delivery=delivery,
        )

        cls._schedule_assignment_cancelled_notifications(
            assignment,
            cancelled_by=cancelled_by,
        )

        return assignment

    # ============================================================
    # LOCK DELIVERY
    # ============================================================

    @staticmethod
    def _lock_delivery(
        delivery,
    ):
        """
        Lock the delivery row.

        The delivery row is the synchronization point for
        assignment creation/reuse.
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

    # ============================================================
    # LOCK ASSIGNMENT
    # ============================================================

    @staticmethod
    def _lock_assignment(
        assignment,
    ):
        """
        Lock assignment row before changing state.
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

    # ============================================================
    # LOCK RIDER
    # ============================================================

    @staticmethod
    def _lock_rider(
        rider,
    ):
        """
        Lock RiderProfile.

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

    # ============================================================
    # ASSIGNMENT ACTIVE VALIDATION
    # ============================================================

    @staticmethod
    def _ensure_assignment_active(
        assignment,
    ):
        """
        Ensure assignment is currently active.
        """

        if not assignment.is_active:
            raise InvalidAssignmentState(
                "Assignment is inactive."
            )

    # ============================================================
    # DELIVERY VALIDATION
    # ============================================================

    @classmethod
    def _ensure_delivery_not_terminal(
        cls,
        delivery,
    ):
        """
        Ensure delivery is not terminal.
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
        Delivery may receive an assignment only while:

            PENDING
            WAITING_FOR_RIDER

        If a cancelled Assignment #1 exists, the delivery must
        have been explicitly restarted by admin/staff.
        """

        if delivery.status not in (
            cls.ASSIGNABLE_DELIVERY_STATUSES
        ):
            raise InvalidAssignmentState(
                f"Delivery with status "
                f"'{delivery.status}' cannot "
                f"be assigned."
            )

    @staticmethod
    def _ensure_delivery_status(
        delivery,
        expected,
    ):
        """
        Ensure exact delivery status.
        """

        if delivery.status != expected:
            raise InvalidAssignmentState(
                f"Expected delivery status "
                f"'{expected}' but got "
                f"'{delivery.status}'."
            )

    # ============================================================
    # ASSIGNMENT COUNT
    # ============================================================

    @staticmethod
    def _get_assignment_count(
        delivery,
    ):
        """
        Return the lifetime number of DeliveryAssignment rows.

        IMPORTANT:

        This counts database rows, not assignment lifecycles.

        Therefore:

            Assignment #1
                cancelled
                restarted
                cancelled
                restarted

        still has:

            assignment_count = 1
        """

        if delivery is None:
            return 0

        return (
            DeliveryAssignment.objects
            .filter(
                delivery=delivery,
            )
            .count()
        )

    # ============================================================
    # MAXIMUM ASSIGNMENTS
    # ============================================================

    @staticmethod
    def _get_maximum_rider_assignments(
        config,
    ):
        """
        Return maximum lifetime assignment records.

        Current business rule:

            max_rider_assignments = 1

        <= 0 is treated as unlimited for compatibility with the
        existing configuration service.
        """

        if config is None:
            return 0

        value = getattr(
            config,
            "max_rider_assignments",
            0,
        )

        try:
            return int(value)

        except (
            TypeError,
            ValueError,
        ):
            return 0

    # ============================================================
    # RIDER VALIDATION
    # ============================================================

    @classmethod
    def _ensure_rider_assignable(
        cls,
        rider,
        profile,
        exclude_assignment=None,
    ):
        """
        Validate rider before assigning/reusing Assignment #1.
        """

        if not rider.is_active:
            raise InvalidAssignmentState(
                "Rider account is not active."
            )

        if not rider.is_verified:
            raise InvalidAssignmentState(
                "Rider is not verified."
            )

        rider_role = getattr(
            rider,
            "role",
            None,
        )

        if rider_role != rider.Roles.RIDER:
            raise InvalidAssignmentState(
                "User is not a rider."
            )

        if profile is None:
            raise InvalidAssignmentState(
                "Rider does not have a rider profile."
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
                status__in=(
                    cls.ACTIVE_ASSIGNMENT_STATUSES
                ),
                is_active=True,
            )
            .exclude(
                pk=None,
            )
            .exists()
        )

        if exclude_assignment is not None:
            has_active_assignment = has_active_assignment.exclude(
                pk = exclude_assignment.pk
            )

        if has_active_assignment.exist():
            raise InvalidAssignmentState(
                "Rider already has an active "
                "assignment."
            )

    # ============================================================
    # ADMIN / STAFF VALIDATION
    # ============================================================

    @staticmethod
    def _ensure_admin_or_staff(
        user,
    ):
        """
        Validate admin/staff authorization.
        """

        if user is None:
            raise InvalidAssignmentState(
                "Admin/staff user is required."
            )

        if not getattr(
            user,
            "is_active",
            False,
        ):
            raise InvalidAssignmentState(
                "Admin/staff account is not active."
            )

        if not (
            getattr(
                user,
                "is_staff",
                False,
            )
            or getattr(
                user,
                "is_superuser",
                False,
            )
        ):
            raise InvalidAssignmentState(
                "Only admin/staff users may perform "
                "this operation."
            )

    # ============================================================
    # ASSIGNMENT STATUS VALIDATION
    # ============================================================

    @staticmethod
    def _ensure_status(
        assignment,
        expected,
    ):
        """
        Ensure assignment has expected status.
        """

        if assignment.status != expected:
            raise InvalidAssignmentState(
                f"Expected assignment status "
                f"'{expected}' but got "
                f"'{assignment.status}'."
            )

    # ============================================================
    # UPDATE ASSIGNMENT STATUS
    # ============================================================

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

    # ============================================================
    # UPDATE DELIVERY STATUS
    # ============================================================

    @staticmethod
    def _update_delivery_status(
        delivery,
        status,
    ):
        """
        Update delivery status and corresponding timestamp.
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
            )
        )

    # ============================================================
    # RIDER AVAILABILITY
    # ============================================================

    @staticmethod
    def _set_rider_availability(
        profile,
        available,
    ):
        """
        Update rider availability.
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

    # ============================================================
    # RIDER AVAILABILITY IF FREE
    # ============================================================

    @classmethod
    def _set_rider_availability_if_free(
        cls,
        rider,
    ):
        """
        Make rider available if no active assignment remains.
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

    # ============================================================
    # CANCEL SELECTED PENDING OFFERS
    # ============================================================

    @staticmethod
    def _cancel_pending_offers(
        delivery,
        accepted_rider,
    ):
        """
        Cancel all pending offers except the selected rider.
        """

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

    # ============================================================
    # CANCEL ALL PENDING OFFERS
    # ============================================================

    @staticmethod
    def _cancel_all_pending_offers(
        delivery,
    ):
        """
        Cancel every pending offer.
        """

        (
            DeliveryOffer.objects
            .filter(
                delivery=delivery,
                status=DeliveryOffer.Status.PENDING,
            )
            .update(
                status=DeliveryOffer.Status.CANCELLED,
                responded_at=timezone.now(),
            )
        )

    # ============================================================
    # ASSIGNMENT NOTIFICATIONS
    # ============================================================

    @staticmethod
    def _schedule_assignment_notifications(
        assignment,
    ):
        """
        Notify relevant parties after assignment transaction
        commits.
        """

        from .notifier import DispatchNotifier

        def notify():

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
                    pass

        transaction.on_commit(
            notify,
        )

    # ============================================================
    # CANCELLATION NOTIFICATIONS
    # ============================================================

    @staticmethod
    def _schedule_assignment_cancelled_notifications(
        assignment,
        cancelled_by,
    ):
        """
        Notify relevant parties after administrative
        cancellation.
        """

        from .notifier import DispatchNotifier

        def notify():

            notify_method = getattr(
                DispatchNotifier,
                "notify_assignment_cancelled",
                None,
            )

            if notify_method is None:
                return

            try:

                notify_method(
                    assignment,
                    cancelled_by=cancelled_by,
                )

            except Exception:
                pass

        transaction.on_commit(
            notify,
        )