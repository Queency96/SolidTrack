from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from deliveries.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
)

from .exceptions import InvalidOfferState


class DeliveryOfferService:
    """
    Service responsible exclusively for the DeliveryOffer lifecycle.

    Responsibilities
    ----------------
    - Create offers
    - Accept offers
    - Reject offers
    - Expire offers
    - Cancel pending offers
    - Validate offer state
    - Lock offer/delivery rows where required

    NOT responsible for
    -------------------
    - Creating DeliveryAssignment
    - Accepting DeliveryAssignment
    - Completing assignments
    - Cancelling assignments
    - Reassigning riders
    - Managing rider availability
    - Redispatching
    - Notifications
    - Dispatch orchestration

    Those responsibilities belong to:

        AssignmentService
        DispatchCoordinator
        DispatchPipeline
        DispatchNotifier

    Assignment reuse
    ----------------
    This service supports the project's single-assignment-row
    architecture.

    A delivery may receive a new rider offer when:

        1. It has never had an assignment, OR
        2. It has a CANCELLED assignment and the delivery has
           explicitly been restarted into WAITING_FOR_RIDER.

    In case (2), this service does NOT create another assignment.

    AssignmentService is responsible for reusing the existing
    cancelled DeliveryAssignment when the new offer is accepted.
    """

    # ============================================================
    # OFFER LIFECYCLE
    # ============================================================

    """
    PENDING
        ├── ACCEPTED
        ├── REJECTED
        ├── EXPIRED
        └── CANCELLED

    An offer can never return to PENDING.
    """

    # ============================================================
    # CREATE OFFER
    # ============================================================

    @classmethod
    @transaction.atomic
    def create(
        cls,
        delivery,
        rider,
        radius,
        timeout,
    ):
        """
        Create a new PENDING DeliveryOffer.

        Rules
        -----
        - Delivery is required.
        - Rider is required.
        - Timeout must be a positive integer.
        - Radius must be a positive number.
        - Delivery must be eligible for dispatch.
        - A rider cannot have another PENDING offer for
          the same delivery.
        - An active/completed assignment prevents a new offer.
        - A CANCELLED assignment may be reused only when the
          delivery is explicitly WAITING_FOR_RIDER.
        - This method never creates a DeliveryAssignment.

        Assignment lifecycle remains exclusively owned by
        AssignmentService.
        """

        # --------------------------------------------------------
        # Validate required values
        # --------------------------------------------------------

        if delivery is None:
            raise InvalidOfferState(
                "Delivery is required to create an offer."
            )

        if rider is None:
            raise InvalidOfferState(
                "Rider is required to create an offer."
            )

        # --------------------------------------------------------
        # Normalize timeout
        # --------------------------------------------------------

        timeout = cls._validate_timeout(
            timeout
        )

        # --------------------------------------------------------
        # Normalize search radius
        # --------------------------------------------------------

        radius = cls._validate_radius(
            radius
        )

        # --------------------------------------------------------
        # Validate rider primary key
        # --------------------------------------------------------

        rider_id = getattr(
            rider,
            "pk",
            None,
        )

        if rider_id is None:
            raise InvalidOfferState(
                "Rider must be a persisted database object."
            )

        # --------------------------------------------------------
        # Lock delivery
        #
        # Delivery is the synchronization point for dispatch.
        #
        # Global lock order:
        #
        #     Delivery
        #         ↓
        #     Offer / Assignment
        #         ↓
        #     RiderProfile
        #
        # This prevents inconsistent locking across services.
        # --------------------------------------------------------

        delivery = cls._lock_delivery(
            delivery
        )

        # --------------------------------------------------------
        # Validate delivery
        # --------------------------------------------------------

        cls._validate_delivery(
            delivery
        )

        # --------------------------------------------------------
        # Prevent duplicate pending offer
        #
        # Delivery is already locked, so all callers using this
        # service serialize offer creation for this delivery.
        # --------------------------------------------------------

        existing_offer = (
            DeliveryOffer.objects
            .filter(
                delivery_id=delivery.pk,
                rider_id=rider_id,
                status=DeliveryOffer.Status.PENDING,
            )
            .first()
        )

        if existing_offer:
            raise InvalidOfferState(
                "This rider already has a pending "
                "offer for this delivery."
            )

        # --------------------------------------------------------
        # Calculate expiration
        # --------------------------------------------------------

        now = timezone.now()

        expires_at = now + timedelta(
            seconds=timeout
        )

        # --------------------------------------------------------
        # Create offer
        # --------------------------------------------------------

        return DeliveryOffer.objects.create(
            delivery=delivery,
            rider=rider,
            search_radius=radius,
            expires_at=expires_at,
            status=DeliveryOffer.Status.PENDING,
        )

    # ============================================================
    # ACCEPT OFFER
    # ============================================================

    @classmethod
    @transaction.atomic
    def accept(cls, offer):
        """
        Mark a pending DeliveryOffer as ACCEPTED.

        IMPORTANT
        ---------
        This method does NOT create a DeliveryAssignment.

        Assignment creation/reuse belongs exclusively to:

            AssignmentService.assign()

        The orchestration layer is responsible for:

            1. Lock delivery
            2. Lock offer
            3. Validate offer
            4. Accept offer
            5. Create/reuse assignment
            6. Accept assignment

        Lock order
        ----------
        Delivery is locked before Offer.

        This follows the project's global locking convention:

            Delivery
                ↓
            Offer / Assignment
                ↓
            RiderProfile

        Returns
        -------
        DeliveryOffer
            The accepted offer.

        Raises
        ------
        InvalidOfferState
            If the offer is missing, expired, or no longer pending.
        """

        # --------------------------------------------------------
        # Validate offer object before accessing its ID
        # --------------------------------------------------------

        if offer is None:
            raise InvalidOfferState(
                "Delivery offer is required."
            )

        offer_id = getattr(
            offer,
            "pk",
            None,
        )

        if offer_id is None:
            raise InvalidOfferState(
                "Invalid delivery offer."
            )

        # --------------------------------------------------------
        # Retrieve the offer without locking first.
        #
        # We need delivery_id so that Delivery can be locked first.
        # --------------------------------------------------------

        try:
            offer_snapshot = (
                DeliveryOffer.objects
                .select_related("delivery")
                .get(
                    pk=offer_id
                )
            )

        except DeliveryOffer.DoesNotExist as exc:
            raise InvalidOfferState(
                "Delivery offer does not exist."
            ) from exc

        # --------------------------------------------------------
        # Lock delivery FIRST
        # --------------------------------------------------------

        delivery = cls._lock_delivery(
            offer_snapshot.delivery_id
        )

        # --------------------------------------------------------
        # Lock offer SECOND
        # --------------------------------------------------------

        locked_offer = cls._lock_offer(
            offer_id
        )

        # --------------------------------------------------------
        # Ensure offer belongs to the locked delivery
        # --------------------------------------------------------

        if locked_offer.delivery_id != delivery.pk:
            raise InvalidOfferState(
                "Delivery offer does not belong to "
                "the expected delivery."
            )

        # --------------------------------------------------------
        # Validate offer
        # --------------------------------------------------------

        cls._validate_actionable(
            locked_offer,
            action="accept",
        )

        # --------------------------------------------------------
        # Validate delivery
        #
        # This intentionally allows:
        #
        #     CANCELLED assignment
        #             +
        #     WAITING_FOR_RIDER
        #
        # because AssignmentService will reuse that assignment.
        # --------------------------------------------------------

        cls._validate_delivery(
            delivery
        )

        # --------------------------------------------------------
        # Mark offer accepted
        # --------------------------------------------------------

        return cls._update_status(
            offer=locked_offer,
            status=DeliveryOffer.Status.ACCEPTED,
        )

    # ============================================================
    # REJECT OFFER
    # ============================================================

    @classmethod
    @transaction.atomic
    def reject(
        cls,
        offer,
        reason="",
    ):
        """
        Reject a pending DeliveryOffer.

        Lifecycle:

            PENDING
                ↓
            REJECTED

        No assignment is created.

        Rejection does not consume the maximum rider assignment
        allowance.

        DispatchCoordinator is responsible for deciding whether
        another rider should subsequently be offered the delivery.
        """

        # --------------------------------------------------------
        # Lock offer
        # --------------------------------------------------------

        offer = cls._lock_offer(
            offer
        )

        # --------------------------------------------------------
        # Validate offer
        # --------------------------------------------------------

        cls._validate_actionable(
            offer,
            action="reject",
        )

        # --------------------------------------------------------
        # Normalize rejection reason
        # --------------------------------------------------------

        reason = (
            str(reason).strip()
            if reason is not None
            else ""
        )

        # --------------------------------------------------------
        # Update state
        # --------------------------------------------------------

        return cls._update_status(
            offer=offer,
            status=DeliveryOffer.Status.REJECTED,
            rejection_reason=reason,
        )

    # ============================================================
    # EXPIRE OFFER
    # ============================================================

    @classmethod
    @transaction.atomic
    def expire(cls, offer):
        """
        Expire a pending DeliveryOffer.

        An offer can only be expired after expires_at.

        Lifecycle:

            PENDING
                ↓
            EXPIRED

        No assignment is created.

        Expiration does not consume the maximum rider assignment
        allowance.
        """

        # --------------------------------------------------------
        # Lock offer
        # --------------------------------------------------------

        offer = cls._lock_offer(
            offer
        )

        # --------------------------------------------------------
        # Validate status
        # --------------------------------------------------------

        if offer.status != DeliveryOffer.Status.PENDING:
            raise InvalidOfferState(
                f"Offer with status "
                f"'{offer.status}' cannot be expired."
            )

        # --------------------------------------------------------
        # Validate expiration timestamp
        # --------------------------------------------------------

        if offer.expires_at is None:
            raise InvalidOfferState(
                "This delivery offer has no expiration time."
            )

        # --------------------------------------------------------
        # Check expiration
        # --------------------------------------------------------

        now = timezone.now()

        if offer.expires_at > now:
            raise InvalidOfferState(
                "This delivery offer has not expired yet."
            )

        # --------------------------------------------------------
        # Update status
        # --------------------------------------------------------

        return cls._update_status(
            offer=offer,
            status=DeliveryOffer.Status.EXPIRED,
        )

    # ============================================================
    # CANCEL OFFER
    # ============================================================

    @classmethod
    @transaction.atomic
    def cancel(cls, offer):
        """
        Cancel a pending DeliveryOffer.

        Lifecycle:

            PENDING
                ↓
            CANCELLED

        This cancels only the offer.

        It does NOT:
            - cancel an assignment
            - change rider availability
            - redispatch
            - send notifications

        Those responsibilities belong elsewhere.

        An accepted offer cannot be cancelled through this method.
        """

        # --------------------------------------------------------
        # Lock offer
        # --------------------------------------------------------

        offer = cls._lock_offer(
            offer
        )

        # --------------------------------------------------------
        # Validate offer
        # --------------------------------------------------------

        cls._validate_actionable(
            offer,
            action="cancel",
        )

        # --------------------------------------------------------
        # Update state
        # --------------------------------------------------------

        return cls._update_status(
            offer=offer,
            status=DeliveryOffer.Status.CANCELLED,
        )

    # ============================================================
    # LOCK OFFER
    # ============================================================

    @staticmethod
    def _lock_offer(offer):
        """
        Retrieve and lock a DeliveryOffer row.

        The returned object is the database-authoritative
        version of the offer.

        This method accepts either:

            DeliveryOffer instance
            DeliveryOffer primary key
        """

        if offer is None:
            raise InvalidOfferState(
                "Delivery offer is required."
            )

        # --------------------------------------------------------
        # Resolve primary key
        # --------------------------------------------------------

        if isinstance(
            offer,
            DeliveryOffer,
        ):
            offer_id = offer.pk

        else:
            offer_id = getattr(
                offer,
                "pk",
                offer,
            )

        if offer_id is None:
            raise InvalidOfferState(
                "Invalid delivery offer."
            )

        # --------------------------------------------------------
        # Lock row
        # --------------------------------------------------------

        try:
            return (
                DeliveryOffer.objects
                .select_for_update()
                .select_related(
                    "delivery",
                    "rider",
                )
                .get(
                    pk=offer_id
                )
            )

        except DeliveryOffer.DoesNotExist as exc:
            raise InvalidOfferState(
                "Delivery offer does not exist."
            ) from exc

    # ============================================================
    # LOCK DELIVERY
    # ============================================================

    @staticmethod
    def _lock_delivery(delivery):
        """
        Retrieve and lock a Delivery row.

        Delivery acts as the synchronization point for
        dispatch and assignment operations.

        The method accepts either:

            Delivery instance
            Delivery primary key
        """

        if delivery is None:
            raise InvalidOfferState(
                "Delivery is required."
            )

        # --------------------------------------------------------
        # Resolve primary key
        # --------------------------------------------------------

        delivery_id = getattr(
            delivery,
            "pk",
            delivery,
        )

        if delivery_id is None:
            raise InvalidOfferState(
                "Invalid delivery."
            )

        # --------------------------------------------------------
        # Lock row
        # --------------------------------------------------------

        try:
            return (
                Delivery.objects
                .select_for_update()
                .get(
                    pk=delivery_id
                )
            )

        except Delivery.DoesNotExist as exc:
            raise InvalidOfferState(
                "Delivery does not exist."
            ) from exc

    # ============================================================
    # VALIDATE ACTIONABLE OFFER
    # ============================================================

    @staticmethod
    def _validate_actionable(
        offer,
        action,
    ):
        """
        Validate whether an offer can perform an action.

        Supported actions:

            accept
            reject
            cancel

        Only PENDING offers may perform these actions.

        Expiration is checked here so a rider cannot interact
        with an offer whose expiration time has already passed.
        """

        if offer is None:
            raise InvalidOfferState(
                "Delivery offer is required."
            )

        # --------------------------------------------------------
        # Status validation
        # --------------------------------------------------------

        if offer.status != DeliveryOffer.Status.PENDING:
            raise InvalidOfferState(
                f"Offer with status "
                f"'{offer.status}' cannot be "
                f"{action}ed."
            )

        # --------------------------------------------------------
        # Expiration timestamp
        # --------------------------------------------------------

        if offer.expires_at is None:
            raise InvalidOfferState(
                "This delivery offer has no expiration time."
            )

        # --------------------------------------------------------
        # Expiration validation
        # --------------------------------------------------------

        if offer.expires_at <= timezone.now():
            raise InvalidOfferState(
                "This delivery offer has expired."
            )

    # ============================================================
    # UPDATE STATUS
    # ============================================================

    @staticmethod
    def _update_status(
        offer,
        status,
        **extra_fields,
    ):
        """
        Safely update a DeliveryOffer lifecycle state.

        Rules
        -----
        - PENDING can never be restored.
        - Terminal states cannot transition to another
          terminal state.
        - responded_at is recorded for terminal transitions.
        - updated_at is included when available.
        """

        if offer is None:
            raise InvalidOfferState(
                "Delivery offer is required."
            )

        # --------------------------------------------------------
        # Prevent transition back to PENDING
        # --------------------------------------------------------

        if status == DeliveryOffer.Status.PENDING:
            raise InvalidOfferState(
                "Lifecycle update cannot transition "
                "an offer back to PENDING."
            )

        # --------------------------------------------------------
        # Terminal states
        # --------------------------------------------------------

        terminal_statuses = {
            DeliveryOffer.Status.ACCEPTED,
            DeliveryOffer.Status.REJECTED,
            DeliveryOffer.Status.EXPIRED,
            DeliveryOffer.Status.CANCELLED,
        }

        # --------------------------------------------------------
        # Prevent terminal → terminal transitions
        # --------------------------------------------------------

        if (
            offer.status in terminal_statuses
            and offer.status != status
        ):
            raise InvalidOfferState(
                f"Offer with status "
                f"'{offer.status}' cannot be "
                f"changed to '{status}'."
            )

        # --------------------------------------------------------
        # Prevent same-status update
        # --------------------------------------------------------

        if offer.status == status:
            raise InvalidOfferState(
                f"Offer is already in status '{status}'."
            )

        # --------------------------------------------------------
        # Update status
        # --------------------------------------------------------

        now = timezone.now()

        offer.status = status
        offer.responded_at = now

        update_fields = [
            "status",
            "responded_at",
        ]

        # --------------------------------------------------------
        # Additional fields
        # --------------------------------------------------------

        for field_name, value in extra_fields.items():

            if not hasattr(
                offer,
                field_name,
            ):
                raise InvalidOfferState(
                    f"DeliveryOffer does not have "
                    f"field '{field_name}'."
                )

            setattr(
                offer,
                field_name,
                value,
            )

            update_fields.append(
                field_name
            )

        # --------------------------------------------------------
        # updated_at
        # --------------------------------------------------------

        if hasattr(
            offer,
            "updated_at",
        ):
            update_fields.append(
                "updated_at"
            )

        # --------------------------------------------------------
        # Save
        # --------------------------------------------------------

        offer.save(
            update_fields=list(
                dict.fromkeys(
                    update_fields
                )
            )
        )

        return offer

    # ============================================================
    # VALIDATE DELIVERY
    # ============================================================

    @classmethod
    def _validate_delivery(cls, delivery):
        """
        Validate whether a Delivery can receive a rider offer.

        Valid delivery states:

            PENDING
            WAITING_FOR_RIDER

        Assignment rules
        ----------------
        No assignment exists:
            → offer allowed

        CANCELLED assignment + WAITING_FOR_RIDER:
            → offer allowed

        Active assignment:
            → offer rejected

        COMPLETED assignment:
            → offer rejected

        This method does NOT create or reuse assignments.

        AssignmentService remains the final authority for
        assignment creation/reuse and rider assignment limits.
        """

        if delivery is None:
            raise InvalidOfferState(
                "Delivery is required."
            )

        # --------------------------------------------------------
        # Validate delivery status
        # --------------------------------------------------------

        assignable_statuses = {
            Delivery.DeliveryStatus.PENDING,
            Delivery.DeliveryStatus.WAITING_FOR_RIDER,
        }

        if delivery.status not in assignable_statuses:
            raise InvalidOfferState(
                f"Delivery with status "
                f"'{delivery.status}' cannot "
                f"receive a rider offer."
            )

        # --------------------------------------------------------
        # Existing direct rider
        #
        # Some Delivery implementations may expose rider_id.
        #
        # If populated, the delivery is already assigned and
        # therefore cannot receive another offer.
        # --------------------------------------------------------

        rider_id = getattr(
            delivery,
            "rider_id",
            None,
        )

        if rider_id:
            raise InvalidOfferState(
                "Delivery already has a rider assigned."
            )

        # --------------------------------------------------------
        # Locate lifetime assignment
        #
        # The project architecture permits at most one
        # DeliveryAssignment row during the delivery lifetime.
        # --------------------------------------------------------

        assignment = (
            DeliveryAssignment.objects
            .filter(
                delivery_id=delivery.pk,
            )
            .order_by("-pk")
            .first()
        )

        # --------------------------------------------------------
        # No historical assignment
        # --------------------------------------------------------

        if assignment is None:
            return

        # --------------------------------------------------------
        # Existing assignment status
        # --------------------------------------------------------

        assignment_status = assignment.status

        # --------------------------------------------------------
        # CANCELLED assignment
        #
        # This is the only historical assignment state that may
        # participate in a new dispatch cycle.
        #
        # The delivery MUST explicitly be WAITING_FOR_RIDER.
        #
        # AssignmentService.assign() will later reuse this same
        # assignment row.
        # --------------------------------------------------------

        if (
            assignment_status
            == DeliveryAssignment.Status.CANCELLED
        ):

            if (
                delivery.status
                != Delivery.DeliveryStatus.WAITING_FOR_RIDER
            ):
                raise InvalidOfferState(
                    "A cancelled assignment can only "
                    "receive a new rider offer after "
                    "the delivery has been restarted "
                    "into WAITING_FOR_RIDER."
                )

            return

        # --------------------------------------------------------
        # COMPLETED assignment
        #
        # A completed assignment can never be reused.
        # --------------------------------------------------------

        if (
            assignment_status
            == DeliveryAssignment.Status.COMPLETED
        ):
            raise InvalidOfferState(
                "Delivery already has a completed "
                "rider assignment."
            )

        # --------------------------------------------------------
        # Any other assignment state is considered active.
        #
        # Examples include:
        #
        #     ASSIGNED
        #     ACCEPTED
        #     EN_ROUTE_PICKUP
        #     ARRIVED_PICKUP
        #     PICKED_UP
        #     OUT_FOR_DELIVERY
        #     ARRIVED_DESTINATION
        #
        # These states must never receive another offer.
        # --------------------------------------------------------

        raise InvalidOfferState(
            f"Delivery already has an active rider "
            f"assignment with status "
            f"'{assignment_status}'."
        )

    # ============================================================
    # VALIDATE TIMEOUT
    # ============================================================

    @staticmethod
    def _validate_timeout(timeout):
        """
        Normalize and validate offer timeout.

        Returns
        -------
        int
            Timeout in seconds.

        Rules
        -----
        - Required.
        - Must be numeric/integer-compatible.
        - Must be greater than zero.
        - Fractional seconds are rejected rather than silently
          truncated.
        """

        if timeout is None:
            raise InvalidOfferState(
                "Offer timeout is required."
            )

        # --------------------------------------------------------
        # Decimal normalization
        # --------------------------------------------------------

        try:
            normalized = Decimal(
                str(timeout)
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise InvalidOfferState(
                "Offer timeout must be a valid number."
            ) from exc

        # --------------------------------------------------------
        # Positive value
        # --------------------------------------------------------

        if normalized <= Decimal("0"):
            raise InvalidOfferState(
                "Offer timeout must be greater than zero."
            )

        # --------------------------------------------------------
        # Whole seconds only
        # --------------------------------------------------------

        if normalized != normalized.to_integral_value():
            raise InvalidOfferState(
                "Offer timeout must be a whole "
                "number of seconds."
            )

        # --------------------------------------------------------
        # Convert to integer
        # --------------------------------------------------------

        timeout_seconds = int(
            normalized
        )

        if timeout_seconds <= 0:
            raise InvalidOfferState(
                "Offer timeout must be at least one second."
            )

        return timeout_seconds

    # ============================================================
    # VALIDATE RADIUS
    # ============================================================

    @staticmethod
    def _validate_radius(radius):
        """
        Normalize and validate search radius.

        Returns
        -------
        Decimal
            Positive search radius.
        """

        if radius is None:
            raise InvalidOfferState(
                "Search radius is required."
            )

        try:
            radius = Decimal(
                str(radius)
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise InvalidOfferState(
                "Search radius must be a valid number."
            ) from exc

        if radius <= Decimal("0"):
            raise InvalidOfferState(
                "Search radius must be greater than zero."
            )

        return radius