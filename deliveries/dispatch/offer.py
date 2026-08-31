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
    Handles the lifecycle of DeliveryOffer.

    ============================================================
    RESPONSIBILITIES
    ============================================================

    This service is responsible for:

        • Creating offers
        • Accepting offers
        • Rejecting offers
        • Expiring offers
        • Cancelling pending offers
        • Validating offer state
        • Locking offer/delivery rows where required

    This service does NOT directly manage:

        • DeliveryAssignment lifecycle
        • Rider availability
        • Rider assignment state transitions
        • Assignment cancellation
        • Redispatch logic
        • Notifications

    Assignment responsibilities belong to:

        AssignmentService

    Dispatch responsibilities belong to:

        DispatchCoordinator
        DispatchPipeline

    Notification responsibilities belong to:

        DispatchNotifier


    ============================================================
    OFFER LIFECYCLE
    ============================================================

        PENDING
            ├── ACCEPTED
            ├── REJECTED
            ├── EXPIRED
            └── CANCELLED

    An offer can never return to PENDING.


    ============================================================
    OFFER VS ASSIGNMENT
    ============================================================

    DeliveryOffer != DeliveryAssignment

    DeliveryOffer:

        Temporary invitation sent to a rider.

    DeliveryAssignment:

        Actual rider assignment created after
        the rider accepts the offer.


    ============================================================
    ACCEPTANCE FLOW
    ============================================================

    When a rider accepts an offer:

        1. Lock the offer.
        2. Validate that it is still actionable.
        3. Lock the delivery.
        4. Mark the offer ACCEPTED.
        5. Ask AssignmentService to create the assignment.
        6. AssignmentService creates ASSIGNED assignment.
        7. AssignmentService marks rider unavailable.
        8. AssignmentService changes delivery to RIDER_ASSIGNED.
        9. AssignmentService cancels competing pending offers.
        10. AssignmentService changes assignment to ACCEPTED.
        11. Delivery becomes RIDER_ACCEPTED.

    All of these operations occur inside one database transaction.

    Therefore, if assignment creation fails:

        Offer acceptance is rolled back.

    This prevents:

        Offer = ACCEPTED
        Assignment = does not exist


    ============================================================
    MAXIMUM ASSIGNMENT RULE
    ============================================================

    The project uses:

        max_rider_assignments = 1

    Therefore a delivery may have only one
    DeliveryAssignment during its lifetime.

    Example:

        Rider A → rejected
        Rider B → expired
        Rider C → cancelled
        Rider D → accepted
        Rider D → Assignment #1

    After Assignment #1 exists:

        Rider E → cannot receive another assignment.


    ============================================================
    IMPORTANT
    ============================================================

    DeliveryOfferService does NOT manually check or increment
    the assignment count.

    AssignmentService is the single authority responsible for
    enforcing:

        max_rider_assignments

    This avoids duplicated business logic.
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

        A rider cannot have multiple pending offers for the
        same delivery.

        The delivery row is locked before validation.

        This method does NOT create a DeliveryAssignment.
        """

        # --------------------------------------------------------
        # Required values
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
        # Validate timeout
        # --------------------------------------------------------

        timeout = cls._validate_timeout(
            timeout,
        )

        # --------------------------------------------------------
        # Validate radius
        # --------------------------------------------------------

        radius = cls._validate_radius(
            radius,
        )

        # --------------------------------------------------------
        # Lock delivery
        # --------------------------------------------------------

        delivery = cls._lock_delivery(
            delivery,
        )

        # --------------------------------------------------------
        # Validate delivery
        # --------------------------------------------------------

        cls._validate_delivery(
            delivery,
        )

        # --------------------------------------------------------
        # Prevent duplicate pending offer
        # --------------------------------------------------------

        existing_offer = (
            DeliveryOffer.objects
            .filter(
                delivery_id=delivery.pk,
                rider_id=rider.pk,
                status=(
                    DeliveryOffer.Status.PENDING
                ),
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

        expires_at = (
            now
            + timedelta(
                seconds=timeout,
            )
        )

        # --------------------------------------------------------
        # Create offer
        # --------------------------------------------------------

        return DeliveryOffer.objects.create(
            delivery=delivery,
            rider=rider,
            search_radius=radius,
            expires_at=expires_at,
            status=(
                DeliveryOffer.Status.PENDING
            ),
        )

    # ============================================================
    # ACCEPT OFFER
    # ============================================================

    @classmethod
    @transaction.atomic
    def accept(
        cls,
        offer,
    ):
        """
        Accept a DeliveryOffer and create the corresponding
        DeliveryAssignment.

        Complete lifecycle:

            OFFER

                PENDING
                    ↓
                ACCEPTED

            ASSIGNMENT

                does not exist
                    ↓
                ASSIGNED
                    ↓
                ACCEPTED

            DELIVERY

                WAITING_FOR_RIDER
                    ↓
                RIDER_ASSIGNED
                    ↓
                RIDER_ACCEPTED


        IMPORTANT
        ---------

        Assignment creation is delegated to AssignmentService.

        This service never directly creates a DeliveryAssignment.

        The complete operation is atomic.

        If AssignmentService.assign() fails:

            • Offer acceptance rolls back.
            • No assignment remains.
            • Rider availability remains unchanged.
            • Delivery status remains unchanged.

        This prevents an inconsistent state such as:

            offer = ACCEPTED
            assignment = missing
        """

        # --------------------------------------------------------
        # Lock offer
        # --------------------------------------------------------

        offer = cls._lock_offer(
            offer,
        )

        # --------------------------------------------------------
        # Validate offer
        # --------------------------------------------------------

        cls._validate_actionable(
            offer,
            action="accept",
        )

        # --------------------------------------------------------
        # Lock delivery
        #
        # AssignmentService will also lock the delivery.
        # Because this service already owns the transaction,
        # PostgreSQL row locking remains safe and serialized.
        # --------------------------------------------------------

        delivery = cls._lock_delivery(
            offer.delivery,
        )

        # --------------------------------------------------------
        # Validate delivery
        #
        # The delivery must still be eligible when the rider
        # accepts the offer.
        # --------------------------------------------------------

        cls._validate_delivery(
            delivery,
        )

        # --------------------------------------------------------
        # Mark offer as accepted
        # --------------------------------------------------------

        now = timezone.now()

        offer.status = (
            DeliveryOffer.Status.ACCEPTED
        )

        offer.responded_at = now

        update_fields = [
            "status",
            "responded_at",
        ]

        if hasattr(
            offer,
            "updated_at",
        ):
            update_fields.append(
                "updated_at",
            )

        offer.save(
            update_fields=update_fields,
        )

        # --------------------------------------------------------
        # Create assignment
        #
        # Import locally to avoid circular imports.
        # --------------------------------------------------------

        from .assignment import AssignmentService

        assignment = (
            AssignmentService.assign(
                delivery=delivery,
                rider=offer.rider,
            )
        )

        # --------------------------------------------------------
        # Move assignment from ASSIGNED → ACCEPTED
        #
        # AssignmentService owns the assignment lifecycle.
        # --------------------------------------------------------

        assignment = (
            AssignmentService.accept(
                assignment,
            )
        )

        # --------------------------------------------------------
        # Return both objects
        #
        # Returning the assignment makes the result immediately
        # useful to the API/coordinator while the accepted offer
        # remains available through offer.
        # --------------------------------------------------------

        return offer, assignment

    # ============================================================
    # REJECT
    # ============================================================

    @classmethod
    @transaction.atomic
    def reject(
        cls,
        offer,
        reason="",
    ):
        """
        Rider rejects a pending offer.

        Lifecycle:

            PENDING
                ↓
            REJECTED

        No assignment is created.

        The delivery remains eligible for another rider offer.
        """

        offer = cls._lock_offer(
            offer,
        )

        cls._validate_actionable(
            offer,
            action="reject",
        )

        reason = (
            str(reason).strip()
            if reason is not None
            else ""
        )

        return cls._update_status(
            offer=offer,
            status=(
                DeliveryOffer.Status.REJECTED
            ),
            rejection_reason=reason,
        )

    # ============================================================
    # EXPIRE
    # ============================================================

    @classmethod
    @transaction.atomic
    def expire(
        cls,
        offer,
    ):
        """
        Expire a pending offer.

        The offer may only be expired after expires_at.

        Lifecycle:

            PENDING
                ↓
            EXPIRED

        No assignment is created.
        """

        offer = cls._lock_offer(
            offer,
        )

        # --------------------------------------------------------
        # Status
        # --------------------------------------------------------

        if (
            offer.status
            != DeliveryOffer.Status.PENDING
        ):
            raise InvalidOfferState(
                f"Offer with status "
                f"'{offer.status}' cannot be expired."
            )

        # --------------------------------------------------------
        # Expiration timestamp
        # --------------------------------------------------------

        if offer.expires_at is None:
            raise InvalidOfferState(
                "This delivery offer has no "
                "expiration time."
            )

        now = timezone.now()

        # --------------------------------------------------------
        # Not expired yet
        # --------------------------------------------------------

        if offer.expires_at > now:
            raise InvalidOfferState(
                "This delivery offer has not "
                "expired yet."
            )

        return cls._update_status(
            offer=offer,
            status=(
                DeliveryOffer.Status.EXPIRED
            ),
        )

    # ============================================================
    # CANCEL OFFER
    # ============================================================

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        offer,
    ):
        """
        Cancel a pending DeliveryOffer.

        This cancels only the offer.

        It does NOT cancel a DeliveryAssignment.

        Lifecycle:

            PENDING
                ↓
            CANCELLED

        Once an offer is ACCEPTED, it cannot be cancelled
        through this method.
        """

        offer = cls._lock_offer(
            offer,
        )

        cls._validate_actionable(
            offer,
            action="cancel",
        )

        return cls._update_status(
            offer=offer,
            status=(
                DeliveryOffer.Status.CANCELLED
            ),
        )

    # ============================================================
    # LOCK OFFER
    # ============================================================

    @staticmethod
    def _lock_offer(
        offer,
    ):
        """
        Lock the DeliveryOffer row before changing state.
        """

        if offer is None:
            raise InvalidOfferState(
                "Delivery offer is required."
            )

        try:
            offer_id = offer.pk

        except AttributeError:
            raise InvalidOfferState(
                "Invalid delivery offer."
            )

        try:
            return (
                DeliveryOffer.objects
                .select_for_update()
                .select_related(
                    "delivery",
                    "rider",
                )
                .get(
                    pk=offer_id,
                )
            )

        except DeliveryOffer.DoesNotExist:
            raise InvalidOfferState(
                "Delivery offer does not exist."
            )

    # ============================================================
    # LOCK DELIVERY
    # ============================================================

    @staticmethod
    def _lock_delivery(
        delivery,
    ):
        """
        Lock the Delivery row.

        The Delivery row is the synchronization point for
        assignment creation.

        AssignmentService also locks the delivery before
        enforcing the lifetime assignment limit.
        """

        if delivery is None:
            raise InvalidOfferState(
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
            raise InvalidOfferState(
                "Delivery does not exist."
            )

    # ============================================================
    # VALIDATE ACTIONABLE OFFER
    # ============================================================

    @staticmethod
    def _validate_actionable(
        offer,
        action,
    ):
        """
        Validate whether an offer can perform a rider action.

        Supported interactive actions:

            • accept
            • reject
            • cancel

        Only PENDING offers can perform these actions.

        Expiration is checked here so a rider cannot accept,
        reject, or cancel an already expired offer.
        """

        # --------------------------------------------------------
        # Status
        # --------------------------------------------------------

        if (
            offer.status
            != DeliveryOffer.Status.PENDING
        ):
            raise InvalidOfferState(
                f"Offer with status "
                f"'{offer.status}' cannot be "
                f"{action}ed."
            )

        # --------------------------------------------------------
        # Expiration
        # --------------------------------------------------------

        if offer.expires_at is None:
            raise InvalidOfferState(
                "This delivery offer has no "
                "expiration time."
            )

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
        Update the DeliveryOffer lifecycle state.

        Rules:

            • PENDING can never be restored.
            • Terminal offers cannot be changed.
            • responded_at is recorded on every terminal state.
        """

        if offer is None:
            raise InvalidOfferState(
                "Delivery offer is required."
            )

        # --------------------------------------------------------
        # Never return to PENDING
        # --------------------------------------------------------

        if (
            status
            == DeliveryOffer.Status.PENDING
        ):
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
        # Update
        # --------------------------------------------------------

        now = timezone.now()

        offer.status = status
        offer.responded_at = now

        update_fields = [
            "status",
            "responded_at",
        ]

        # --------------------------------------------------------
        # Extra fields
        # --------------------------------------------------------

        for field_name, value in extra_fields.items():

            setattr(
                offer,
                field_name,
                value,
            )

            update_fields.append(
                field_name,
            )

        # --------------------------------------------------------
        # updated_at
        # --------------------------------------------------------

        if hasattr(
            offer,
            "updated_at",
        ):
            update_fields.append(
                "updated_at",
            )

        offer.save(
            update_fields=update_fields,
        )

        return offer

    # ============================================================
    # VALIDATE DELIVERY
    # ============================================================

    @classmethod
    def _validate_delivery(
        cls,
        delivery,
    ):
        """
        Ensure the delivery can receive a rider offer.

        Eligible states:

            PENDING
            WAITING_FOR_RIDER

        A delivery that already has an assignment cannot receive
        another offer.

        AssignmentService remains the final authority for the
        lifetime assignment limit.
        """

        if delivery is None:
            raise InvalidOfferState(
                "Delivery is required."
            )

        # --------------------------------------------------------
        # Allowed delivery statuses
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
        # Direct rider relationship
        # --------------------------------------------------------

        if getattr(
            delivery,
            "rider_id",
            None,
        ):
            raise InvalidOfferState(
                "Delivery already has a rider assigned."
            )

        # --------------------------------------------------------
        # Existing assignment
        #
        # This deliberately checks historical assignments, not
        # only active assignments.
        #
        # Therefore a cancelled assignment still prevents a new
        # offer from being created.
        # --------------------------------------------------------

        has_assignment = (
            DeliveryAssignment.objects
            .filter(
                delivery=delivery,
            )
            .exists()
        )

        if has_assignment:
            raise InvalidOfferState(
                "Delivery already has a rider "
                "assignment and cannot receive "
                "another rider offer."
            )

    # ============================================================
    # VALIDATE TIMEOUT
    # ============================================================

    @staticmethod
    def _validate_timeout(
        timeout,
    ):
        """
        Normalize and validate offer timeout.
        """

        if timeout is None:
            raise InvalidOfferState(
                "Offer timeout is required."
            )

        try:
            timeout = int(
                timeout,
            )

        except (
            TypeError,
            ValueError,
        ):
            raise InvalidOfferState(
                "Offer timeout must be a valid integer."
            )

        if timeout <= 0:
            raise InvalidOfferState(
                "Offer timeout must be greater than zero."
            )

        return timeout

    # ============================================================
    # VALIDATE RADIUS
    # ============================================================

    @staticmethod
    def _validate_radius(
        radius,
    ):
        """
        Normalize and validate search radius.
        """

        if radius is None:
            raise InvalidOfferState(
                "Search radius is required."
            )

        try:
            radius = Decimal(
                str(radius),
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):
            raise InvalidOfferState(
                "Search radius must be a valid number."
            )

        if radius <= Decimal("0"):
            raise InvalidOfferState(
                "Search radius must be greater than zero."
            )

        return radius
