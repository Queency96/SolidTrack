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
    Owns the complete DeliveryAssignment lifecycle.

    ============================================================
    CORE INVARIANT
    ============================================================

    One Delivery
        =
    One DeliveryAssignment database row

    The row may be reused only after:

        Assignment:
            CANCELLED + inactive

        Delivery:
            CANCELLED

        Administrative restart:
            explicitly performed

        Delivery:
            WAITING_FOR_RIDER

    A second assignment row is NEVER created.

    ============================================================
    LOCK ORDER
    ============================================================

        Delivery
            ↓
        DeliveryAssignment
            ↓
        RiderProfile

    This ordering must remain consistent throughout the
    assignment lifecycle.

    ============================================================
    RESPONSIBILITIES
    ============================================================

    Owns:

        - assignment creation
        - assignment reuse
        - assignment acceptance
        - pickup lifecycle
        - delivery lifecycle
        - assignment completion
        - administrative cancellation
        - rider availability
        - assignment status
        - delivery status synchronization
        - competing offer cancellation

    Does NOT own:

        - offer lifecycle
        - rider matching
        - rider ranking
        - redispatch orchestration
        - notifications
        - events
    """

    # ============================================================
    # ACTIVE ASSIGNMENT STATUSES
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

    # ============================================================
    # ADMIN CANCELLABLE STATES
    # ============================================================

    ADMIN_CANCELLABLE_STATUSES = (
        DeliveryAssignment.AssignmentStatus.ASSIGNED,
        DeliveryAssignment.AssignmentStatus.ACCEPTED,
        DeliveryAssignment.AssignmentStatus.EN_ROUTE_PICKUP,
        DeliveryAssignment.AssignmentStatus.ARRIVED_PICKUP,
    )

    # ============================================================
    # DELIVERY STATES THAT CAN RECEIVE ASSIGNMENT
    # ============================================================

    ASSIGNABLE_DELIVERY_STATUSES = (
        Delivery.DeliveryStatus.PENDING,
        Delivery.DeliveryStatus.WAITING_FOR_RIDER,
    )

    # ============================================================
    # TERMINAL DELIVERY STATES
    # ============================================================

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
        Create the first assignment or reuse the existing
        cancelled assignment.

        FIRST LIFECYCLE:

            PENDING / WAITING_FOR_RIDER
                ↓
            DeliveryAssignment #1
                ↓
            ASSIGNED

        REUSE LIFECYCLE:

            DeliveryAssignment #1
                ↓
            CANCELLED + inactive

            Delivery
                ↓
            CANCELLED

            explicit administrative restart
                ↓
            WAITING_FOR_RIDER

            rider accepts a new offer
                ↓
            SAME DeliveryAssignment #1
                ↓
            ASSIGNED

        A second DeliveryAssignment row is never created.
        """

        if delivery is None:
            raise InvalidAssignmentState(
                "Delivery is required."
            )

        if rider is None:
            raise InvalidAssignmentState(
                "Rider is required."
            )

        # ========================================================
        # LOCK DELIVERY FIRST
        # ========================================================

        delivery = cls._lock_delivery(
            delivery
        )

        cls._ensure_delivery_assignable(
            delivery
        )

        # ========================================================
        # LOAD ACTIVE CONFIGURATION
        # ========================================================

        config = (
            DispatchConfigurationService
            .get_configuration()
        )

        if config is None:
            raise InvalidAssignmentState(
                "No active dispatch configuration "
                "is available."
            )

        maximum = (
            cls._get_maximum_rider_assignments(
                config
            )
        )

        # ========================================================
        # LOCK EXISTING LIFETIME ASSIGNMENT
        # ========================================================

        assignment = (
            DeliveryAssignment.objects
            .select_for_update()
            .select_related(
                "delivery",
                "rider",
            )
            .filter(
                delivery_id=delivery.pk
            )
            .first()
        )

        # ========================================================
        # FIRST ASSIGNMENT
        # ========================================================

        if assignment is None:

            if maximum > 0:

                assignment_count = (
                    cls._get_assignment_count(
                        delivery
                    )
                )

                if assignment_count >= maximum:
                    raise InvalidAssignmentState(
                        "Maximum rider assignment limit "
                        "has been reached for this delivery."
                    )

        # ========================================================
        # EXISTING ASSIGNMENT
        # ========================================================

        else:

            # ----------------------------------------------------
            # Active assignment
            # ----------------------------------------------------

            if (
                assignment.is_active
                and assignment.status
                in cls.ACTIVE_ASSIGNMENT_STATUSES
            ):
                raise AssignmentAlreadyExists(
                    "Delivery already has an active "
                    "rider assignment."
                )

            # ----------------------------------------------------
            # Completed assignment
            # ----------------------------------------------------

            if (
                assignment.status
                == DeliveryAssignment
                .AssignmentStatus
                .COMPLETED
            ):
                raise AssignmentAlreadyExists(
                    "Completed delivery assignments "
                    "cannot be reused."
                )

            # ----------------------------------------------------
            # Rejected assignment
            # ----------------------------------------------------

            if (
                assignment.status
                == DeliveryAssignment
                .AssignmentStatus
                .REJECTED
            ):
                raise AssignmentAlreadyExists(
                    "Rejected delivery assignments "
                    "cannot be reused."
                )

            # ----------------------------------------------------
            # Failed assignment
            # ----------------------------------------------------

            if (
                assignment.status
                == DeliveryAssignment
                .AssignmentStatus
                .FAILED
            ):
                raise AssignmentAlreadyExists(
                    "Failed delivery assignments "
                    "cannot be reused."
                )

            # ----------------------------------------------------
            # Only CANCELLED can be reused
            # ----------------------------------------------------

            if (
                assignment.status
                != DeliveryAssignment
                .AssignmentStatus
                .CANCELLED
            ):
                raise AssignmentAlreadyExists(
                    "Delivery already has a rider "
                    "assignment. A second assignment "
                    "is not permitted."
                )

            # ----------------------------------------------------
            # Cancelled assignment must be inactive
            # ----------------------------------------------------

            if assignment.is_active:
                raise InvalidAssignmentState(
                    "A cancelled assignment must be "
                    "inactive before it can be reused."
                )

            # ----------------------------------------------------
            # Delivery must have been explicitly restarted
            # ----------------------------------------------------

            if (
                delivery.status
                != Delivery.DeliveryStatus.WAITING_FOR_RIDER
            ):
                raise InvalidAssignmentState(
                    "The cancelled assignment has not "
                    "been explicitly restarted."
                )

        # ========================================================
        # LOCK RIDER AFTER DELIVERY + ASSIGNMENT
        # ========================================================

        rider, rider_profile = cls._lock_rider(
            rider
        )

        # ========================================================
        # VALIDATE RIDER
        # ========================================================

        cls._ensure_rider_assignable(
            rider=rider,
            profile=rider_profile,
            exclude_assignment=assignment,
        )

        # ========================================================
        # CREATE FIRST ASSIGNMENT ROW
        # ========================================================

        if assignment is None:

            assignment = (
                DeliveryAssignment.objects.create(
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
            )

        # ========================================================
        # REUSE EXISTING CANCELLED ROW
        # ========================================================

        else:

            assignment = cls._reset_for_reuse(
                assignment=assignment,
                rider=rider,
                assigned_by=assigned_by,
            )

        # ========================================================
        # RIDER BECOMES UNAVAILABLE
        # ========================================================

        cls._set_rider_availability(
            profile=rider_profile,
            available=False,
        )

        # ========================================================
        # DELIVERY BECOMES ASSIGNED
        # ========================================================

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .RIDER_ASSIGNED
            ),
        )

        # ========================================================
        # CANCEL COMPETING OFFERS
        # ========================================================

        cls._cancel_pending_offers(
            delivery=delivery,
            accepted_rider=rider,
        )

        return assignment

    # ============================================================
    # RESET CANCELLED ASSIGNMENT FOR REUSE
    # ============================================================

    @staticmethod
    def _reset_for_reuse(
        assignment,
        rider,
        assigned_by=None,
    ):
        """
        Reuse the SAME DeliveryAssignment database row.

        The primary key remains unchanged.

        assigned_at remains the original row creation timestamp
        because the model uses auto_now_add=True.

        All previous lifecycle timestamps are cleared.
        """

        if assignment is None:
            raise InvalidAssignmentState(
                "Assignment is required."
            )

        if (
            assignment.status
            != DeliveryAssignment
            .AssignmentStatus
            .CANCELLED
        ):
            raise InvalidAssignmentState(
                "Only a cancelled assignment can be reused."
            )

        if assignment.is_active:
            raise InvalidAssignmentState(
                "Only an inactive cancelled assignment "
                "can be reused."
            )

        assignment.rider = rider
        assignment.assigned_by = assigned_by

        assignment.status = (
            DeliveryAssignment
            .AssignmentStatus
            .ASSIGNED
        )

        assignment.is_active = True

        # --------------------------------------------------------
        # Clear every previous lifecycle timestamp.
        # --------------------------------------------------------

        lifecycle_fields = (
            "accepted_at",
            "rejected_at",
            "en_route_pickup_at",
            "arrived_pickup_at",
            "picked_up_at",
            "out_for_delivery_at",
            "arrived_destination_at",
            "completed_at",
            "cancelled_at",
            "failed_at",
        )

        update_fields = {
            "rider",
            "assigned_by",
            "status",
            "is_active",
        }

        for field_name in lifecycle_fields:

            setattr(
                assignment,
                field_name,
                None,
            )

            update_fields.add(
                field_name
            )

        # --------------------------------------------------------
        # Clear previous reasons.
        # --------------------------------------------------------

        assignment.rejection_reason = ""
        assignment.cancellation_reason = ""
        assignment.failure_reason = ""

        update_fields.update(
            {
                "rejection_reason",
                "cancellation_reason",
                "failure_reason",
            }
        )

        if hasattr(
            assignment,
            "updated_at",
        ):
            update_fields.add(
                "updated_at"
            )

        assignment.save(
            update_fields=list(
                update_fields
            )
        )

        return assignment

    # ============================================================
    # ADMINISTRATIVE RESTART
    # ============================================================

    @classmethod
    @transaction.atomic
    def restart_cancelled_assignment(
        cls,
        assignment,
        restarted_by,
    ):
        """
        Explicit administrative/staff restart.

        REQUIRED:

            Assignment:
                CANCELLED
                inactive

            Delivery:
                CANCELLED

        RESULT:

            Delivery:
                WAITING_FOR_RIDER

            Assignment:
                remains CANCELLED + inactive

        The assignment is reused later by assign().
        """

        cls._ensure_admin_or_staff(
            restarted_by
        )

        if assignment is None:
            raise InvalidAssignmentState(
                "Assignment is required."
            )

        assignment_id = getattr(
            assignment,
            "pk",
            assignment,
        )

        delivery_id = getattr(
            assignment,
            "delivery_id",
            None,
        )

        if not delivery_id:
            raise InvalidAssignmentState(
                "Assignment does not have a delivery."
            )

        # ========================================================
        # LOCK DELIVERY FIRST
        # ========================================================

        delivery = cls._lock_delivery(
            delivery_id
        )

        # ========================================================
        # LOCK ASSIGNMENT SECOND
        # ========================================================

        assignment = cls._lock_assignment(
            assignment_id
        )

        if assignment.delivery_id != delivery.pk:
            raise InvalidAssignmentState(
                "Assignment does not belong to the delivery."
            )

        # ========================================================
        # ASSIGNMENT MUST BE CANCELLED
        # ========================================================

        if (
            assignment.status
            != DeliveryAssignment
            .AssignmentStatus
            .CANCELLED
        ):
            raise InvalidAssignmentState(
                "Only a cancelled assignment "
                "can be restarted."
            )

        if assignment.is_active:
            raise InvalidAssignmentState(
                "A cancelled assignment must be "
                "inactive before restart."
            )

        # ========================================================
        # DELIVERY MUST BE CANCELLED
        # ========================================================

        if (
            delivery.status
            != Delivery.DeliveryStatus.CANCELLED
        ):
            raise InvalidAssignmentState(
                "Only a cancelled delivery can be restarted. "
                f"Current status is '{delivery.status}'."
            )

        # ========================================================
        # CANCEL STALE PENDING OFFERS
        # ========================================================

        cls._cancel_all_pending_offers(
            delivery=delivery
        )

        # ========================================================
        # REOPEN DISPATCH
        # ========================================================

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .WAITING_FOR_RIDER
            ),
        )

        # --------------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT change assignment status here.
        #
        # It remains:
        #
        #     CANCELLED + inactive
        #
        # until assign() reuses the same row.
        # --------------------------------------------------------

        return assignment

    # ============================================================
    # ACCEPT
    # ============================================================

    @classmethod
    @transaction.atomic
    def accept(
        cls,
        assignment,
    ):
        """
        ASSIGNED → ACCEPTED

        Delivery:

            RIDER_ASSIGNED → RIDER_ACCEPTED
        """

        assignment, delivery = (
            cls._lock_assignment_and_delivery(
                assignment
            )
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment
            .AssignmentStatus
            .ASSIGNED,
        )

        cls._ensure_assignment_active(
            assignment
        )

        cls._ensure_delivery_status(
            delivery,
            Delivery.DeliveryStatus.RIDER_ASSIGNED,
        )

        now = timezone.now()

        assignment = cls._update_assignment_status(
            assignment=assignment,
            status=(
                DeliveryAssignment
                .AssignmentStatus
                .ACCEPTED
            ),
            accepted_at=now,
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

        assignment, delivery = (
            cls._lock_assignment_and_delivery(
                assignment
            )
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment
            .AssignmentStatus
            .ACCEPTED,
        )

        cls._ensure_assignment_active(
            assignment
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
            en_route_pickup_at=timezone.now(),
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

        assignment, delivery = (
            cls._lock_assignment_and_delivery(
                assignment
            )
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment
            .AssignmentStatus
            .EN_ROUTE_PICKUP,
        )

        cls._ensure_assignment_active(
            assignment
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
            arrived_pickup_at=timezone.now(),
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

        Delivery:

            RIDER_ACCEPTED → PICKED_UP
        """

        assignment, delivery = (
            cls._lock_assignment_and_delivery(
                assignment
            )
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment
            .AssignmentStatus
            .ARRIVED_PICKUP,
        )

        cls._ensure_assignment_active(
            assignment
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
            picked_up_at=timezone.now(),
        )

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .PICKED_UP
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

        Delivery:

            PICKED_UP → IN_TRANSIT
        """

        assignment, delivery = (
            cls._lock_assignment_and_delivery(
                assignment
            )
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment
            .AssignmentStatus
            .PICKED_UP,
        )

        cls._ensure_assignment_active(
            assignment
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
            out_for_delivery_at=timezone.now(),
        )

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .IN_TRANSIT
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

        assignment, delivery = (
            cls._lock_assignment_and_delivery(
                assignment
            )
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment
            .AssignmentStatus
            .OUT_FOR_DELIVERY,
        )

        cls._ensure_assignment_active(
            assignment
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
            arrived_destination_at=timezone.now(),
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

        Delivery:

            IN_TRANSIT → DELIVERED

        Rider:

            unavailable → available

        Completed assignment can NEVER be reused.
        """

        assignment, delivery = (
            cls._lock_assignment_and_delivery(
                assignment
            )
        )

        cls._ensure_status(
            assignment,
            DeliveryAssignment
            .AssignmentStatus
            .ARRIVED_DESTINATION,
        )

        cls._ensure_assignment_active(
            assignment
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
                Delivery.DeliveryStatus
                .DELIVERED
            ),
        )

        cls._set_rider_availability_if_free(
            assignment.rider
        )

        return assignment

    # ============================================================
    # ADMIN / STAFF CANCELLATION
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
        Cancel an active assignment.

        Assignment:

            ACTIVE → CANCELLED + inactive

        Delivery:

            current → CANCELLED

        Rider:

            unavailable → available

        The assignment row remains in the database.

        It may only be reused after:

            admin restart
                ↓
            Delivery = WAITING_FOR_RIDER
                ↓
            assign()
        """

        cls._ensure_admin_or_staff(
            cancelled_by
        )

        if assignment is None:
            raise InvalidAssignmentState(
                "Assignment is required."
            )

        delivery_id = getattr(
            assignment,
            "delivery_id",
            None,
        )

        if not delivery_id:
            raise InvalidAssignmentState(
                "Assignment does not have a delivery."
            )

        # ========================================================
        # LOCK DELIVERY FIRST
        # ========================================================

        delivery = cls._lock_delivery(
            delivery_id
        )

        # ========================================================
        # LOCK ASSIGNMENT SECOND
        # ========================================================

        assignment = cls._lock_assignment(
            assignment.pk
        )

        if assignment.delivery_id != delivery.pk:
            raise InvalidAssignmentState(
                "Assignment does not belong to the delivery."
            )

        cls._ensure_assignment_active(
            assignment
        )

        if assignment.status not in (
            cls.ADMIN_CANCELLABLE_STATUSES
        ):
            raise InvalidAssignmentState(
                f"Assignment with status "
                f"'{assignment.status}' cannot be "
                f"cancelled by admin/staff."
            )

        cls._ensure_delivery_not_terminal(
            delivery
        )

        reason = (
            str(reason).strip()
            if reason is not None
            else ""
        )

        if not reason:
            raise InvalidAssignmentState(
                "A cancellation reason is required."
            )

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

        cls._update_delivery_status(
            delivery=delivery,
            status=(
                Delivery.DeliveryStatus
                .CANCELLED
            ),
        )

        cls._set_rider_availability_if_free(
            assignment.rider
        )

        cls._cancel_all_pending_offers(
            delivery=delivery
        )

        return assignment

    # ============================================================
    # LOCK ASSIGNMENT + DELIVERY
    # ============================================================

    @classmethod
    def _lock_assignment_and_delivery(
        cls,
        assignment,
    ):
        """
        Global lock order:

            Delivery
                ↓
            DeliveryAssignment
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

        delivery_id = getattr(
            assignment,
            "delivery_id",
            None,
        )

        if not delivery_id:

            try:

                delivery_id = (
                    DeliveryAssignment.objects
                    .only("delivery_id")
                    .get(
                        pk=assignment_id
                    )
                    .delivery_id
                )

            except DeliveryAssignment.DoesNotExist as exc:

                raise InvalidAssignmentState(
                    "Assignment does not exist."
                ) from exc

        # Delivery MUST be locked first.
        delivery = cls._lock_delivery(
            delivery_id
        )

        # Assignment MUST be locked second.
        assignment = cls._lock_assignment(
            assignment_id
        )

        if assignment.delivery_id != delivery.pk:
            raise InvalidAssignmentState(
                "Assignment does not belong to its delivery."
            )

        return assignment, delivery

    # ============================================================
    # LOCK DELIVERY
    # ============================================================

    @staticmethod
    def _lock_delivery(
        delivery,
    ):
        """
        Acquire Delivery row lock.

        Delivery is always the first lock.
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
                    pk=delivery_id
                )
            )

        except Delivery.DoesNotExist as exc:

            raise InvalidAssignmentState(
                "Delivery does not exist."
            ) from exc

    # ============================================================
    # LOCK ASSIGNMENT
    # ============================================================

    @staticmethod
    def _lock_assignment(
        assignment,
    ):
        """
        Acquire DeliveryAssignment row lock.

        Must only be called after Delivery is locked.
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
                    pk=assignment_id
                )
            )

        except DeliveryAssignment.DoesNotExist as exc:

            raise InvalidAssignmentState(
                "Assignment does not exist."
            ) from exc

    # ============================================================
    # LOCK RIDER
    # ============================================================

    @staticmethod
    def _lock_rider(
        rider,
    ):
        """
        Lock RiderProfile after Delivery and Assignment.

        RiderProfile is identified using user_id.
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
                    user_id=rider_id
                )
            )

        except RiderProfile.DoesNotExist as exc:

            raise InvalidAssignmentState(
                "Rider does not have a rider profile."
            ) from exc

        return profile.user, profile

    # ============================================================
    # ENSURE ASSIGNMENT ACTIVE
    # ============================================================

    @staticmethod
    def _ensure_assignment_active(
        assignment,
    ):
        if not assignment.is_active:
            raise InvalidAssignmentState(
                "Assignment is inactive."
            )

    # ============================================================
    # ENSURE DELIVERY ASSIGNABLE
    # ============================================================

    @classmethod
    def _ensure_delivery_assignable(
        cls,
        delivery,
    ):
        if delivery.status not in (
            cls.ASSIGNABLE_DELIVERY_STATUSES
        ):
            raise InvalidAssignmentState(
                f"Delivery with status "
                f"'{delivery.status}' cannot be assigned."
            )

    # ============================================================
    # ENSURE DELIVERY NON-TERMINAL
    # ============================================================

    @classmethod
    def _ensure_delivery_not_terminal(
        cls,
        delivery,
    ):
        if delivery.status in (
            cls.TERMINAL_DELIVERY_STATUSES
        ):
            raise InvalidAssignmentState(
                f"Delivery with status "
                f"'{delivery.status}' is terminal."
            )

    # ============================================================
    # ENSURE DELIVERY STATUS
    # ============================================================

    @staticmethod
    def _ensure_delivery_status(
        delivery,
        expected,
    ):
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
        Count lifetime assignment rows.

        With the OneToOne constraint, this can only legitimately
        return:

            0
            1
        """

        if delivery is None:
            return 0

        delivery_id = getattr(
            delivery,
            "pk",
            delivery,
        )

        return (
            DeliveryAssignment.objects
            .filter(
                delivery_id=delivery_id
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
        Return configured maximum assignment count.

        This is only relevant when creating the first assignment
        row because the architecture allows exactly one lifetime
        assignment row.
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
        Final assignment-level rider validation.
        """

        if rider is None:
            raise InvalidAssignmentState(
                "Rider is required."
            )

        if profile is None:
            raise InvalidAssignmentState(
                "Rider does not have a rider profile."
            )

        # ========================================================
        # USER ACTIVE
        # ========================================================

        if not getattr(
            rider,
            "is_active",
            False,
        ):
            raise InvalidAssignmentState(
                "Rider account is not active."
            )

        # ========================================================
        # USER VERIFIED
        # ========================================================

        if not getattr(
            rider,
            "is_verified",
            False,
        ):
            raise InvalidAssignmentState(
                "Rider is not verified."
            )

        # ========================================================
        # RIDER ROLE
        # ========================================================

        roles = getattr(
            rider,
            "Roles",
            None,
        )

        rider_role = getattr(
            rider,
            "role",
            None,
        )

        if roles is not None:

            expected_role = getattr(
                roles,
                "RIDER",
                None,
            )

            if (
                expected_role is not None
                and rider_role != expected_role
            ):
                raise InvalidAssignmentState(
                    "User is not a rider."
                )

        # ========================================================
        # ONLINE
        # ========================================================

        if not getattr(
            profile,
            "is_online",
            False,
        ):
            raise InvalidAssignmentState(
                "Rider is offline."
            )

        # ========================================================
        # AVAILABLE
        # ========================================================

        if not getattr(
            profile,
            "is_available",
            False,
        ):
            raise InvalidAssignmentState(
                "Rider is currently unavailable."
            )

        # ========================================================
        # RIDER VERIFICATION STATUS
        # ========================================================

        verification_status = getattr(
            profile,
            "verification_status",
            None,
        )

        verification_enum = getattr(
            RiderProfile,
            "VerificationStatus",
            None,
        )

        approved_status = (
            getattr(
                verification_enum,
                "APPROVED",
                None,
            )
            if verification_enum is not None
            else None
        )

        if (
            approved_status is not None
            and verification_status != approved_status
        ):
            raise InvalidAssignmentState(
                "Rider verification is not approved."
            )

        # ========================================================
        # OTHER ACTIVE ASSIGNMENTS
        # ========================================================

        queryset = (
            DeliveryAssignment.objects
            .filter(
                rider_id=rider.pk,
                status__in=cls.ACTIVE_ASSIGNMENT_STATUSES,
                is_active=True,
            )
        )

        if exclude_assignment is not None:

            queryset = queryset.exclude(
                pk=exclude_assignment.pk
            )

        if queryset.exists():

            raise InvalidAssignmentState(
                "Rider already has an active "
                "assignment."
            )

    # ============================================================
    # ADMIN / STAFF AUTHORIZATION
    # ============================================================

    @staticmethod
    def _ensure_admin_or_staff(
        user,
    ):
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
        Update assignment status and any lifecycle fields.

        The model's save() performs full_clean(), so all required
        fields must be populated before saving.
        """

        if assignment is None:
            raise InvalidAssignmentState(
                "Assignment is required."
            )

        assignment.status = status

        update_fields = {
            "status",
        }

        for field_name, value in extra_fields.items():

            if not hasattr(
                assignment,
                field_name,
            ):
                raise InvalidAssignmentState(
                    f"DeliveryAssignment does not "
                    f"have field '{field_name}'."
                )

            setattr(
                assignment,
                field_name,
                value,
            )

            update_fields.add(
                field_name
            )

        if hasattr(
            assignment,
            "updated_at",
        ):
            update_fields.add(
                "updated_at"
            )

        assignment.save(
            update_fields=list(
                update_fields
            )
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
        Synchronize Delivery status and its corresponding
        lifecycle timestamp.
        """

        if delivery is None:
            raise InvalidAssignmentState(
                "Delivery is required."
            )

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
            status
        )

        if (
            timestamp_field
            and hasattr(
                delivery,
                timestamp_field,
            )
        ):
            setattr(
                delivery,
                timestamp_field,
                now,
            )

            update_fields.add(
                timestamp_field
            )

        if hasattr(
            delivery,
            "updated_at",
        ):
            update_fields.add(
                "updated_at"
            )

        delivery.save(
            update_fields=list(
                update_fields
            )
        )

        return delivery

    # ============================================================
    # SET RIDER AVAILABILITY
    # ============================================================

    @staticmethod
    def _set_rider_availability(
        profile,
        available,
    ):
        if profile is None:
            raise InvalidAssignmentState(
                "Rider profile does not exist."
            )

        profile.is_available = bool(
            available
        )

        update_fields = [
            "is_available",
        ]

        if hasattr(
            profile,
            "updated_at",
        ):
            update_fields.append(
                "updated_at"
            )

        profile.save(
            update_fields=update_fields
        )

    # ============================================================
    # SET RIDER AVAILABLE IF FREE
    # ============================================================

    @classmethod
    def _set_rider_availability_if_free(
        cls,
        rider,
    ):
        """
        Make rider available only when no other active assignment
        exists.

        RiderProfile is locked before changing availability.
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
                .get(
                    user_id=rider_id
                )
            )

        except RiderProfile.DoesNotExist as exc:

            raise InvalidAssignmentState(
                "Rider profile does not exist."
            ) from exc

        has_active_assignment = (
            DeliveryAssignment.objects
            .filter(
                rider_id=rider_id,
                status__in=cls.ACTIVE_ASSIGNMENT_STATUSES,
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
                    "updated_at"
                )

            profile.save(
                update_fields=update_fields
            )

    # ============================================================
    # CANCEL PENDING OFFERS EXCEPT ACCEPTED RIDER
    # ============================================================

    @staticmethod
    def _cancel_pending_offers(
        delivery,
        accepted_rider,
    ):
        """
        Cancel all pending offers except the accepted rider's offer.
        """

        if delivery is None:
            return

        queryset = (
            DeliveryOffer.objects
            .filter(
                delivery_id=delivery.pk,
                status=(
                    DeliveryOffer
                    .Status
                    .PENDING
                ),
            )
        )

        if accepted_rider is not None:

            rider_id = getattr(
                accepted_rider,
                "pk",
                accepted_rider,
            )

            queryset = queryset.exclude(
                rider_id=rider_id
            )

        queryset.update(
            status=(
                DeliveryOffer
                .Status
                .CANCELLED
            ),
            responded_at=timezone.now(),
        )

    # ============================================================
    # CANCEL ALL PENDING OFFERS
    # ============================================================

    @staticmethod
    def _cancel_all_pending_offers(
        delivery,
    ):
        """
        Cancel every pending offer belonging to the delivery.
        """

        if delivery is None:
            return

        DeliveryOffer.objects.filter(
            delivery_id=delivery.pk,
            status=(
                DeliveryOffer
                .Status
                .PENDING
            ),
        ).update(
            status=(
                DeliveryOffer
                .Status
                .CANCELLED
            ),
            responded_at=timezone.now(),
        )