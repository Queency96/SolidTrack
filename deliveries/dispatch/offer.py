from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from deliveries.models import (
    Delivery,
    DeliveryOffer,
)

from .exceptions import InvalidOfferState


class DeliveryOfferService:
    """
    Handles the complete lifecycle of delivery offers.

    Responsibilities
    ----------------
    • Create offers
    • Accept offers
    • Reject offers
    • Expire offers
    • Cancel offers

    This service does NOT:

        • Create assignments
        • Assign riders
        • Redispatch deliveries
        • Notify users
        • Publish dispatch events

    Those responsibilities belong to:

        AssignmentService
        DispatchCoordinator
        DispatchNotifier
        EventPublisher

    Lifecycle
    ---------
        PENDING
            ├── ACCEPTED
            ├── REJECTED
            ├── EXPIRED
            └── CANCELLED
    """

    # ==================================================
    # Create Offer
    # ==================================================

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
        Create a new pending delivery offer.

        A rider cannot have multiple pending offers
        for the same delivery.

        The delivery row is locked before the offer
        is created to protect against concurrent
        dispatch attempts.
        """

        # ------------------------------------------
        # Validate delivery
        # ------------------------------------------

        if delivery is None:
            raise InvalidOfferState(
                "Delivery is required to create an offer."
            )

        # ------------------------------------------
        # Validate rider
        # ------------------------------------------

        if rider is None:
            raise InvalidOfferState(
                "Rider is required to create an offer."
            )

        # ------------------------------------------
        # Validate timeout
        # ------------------------------------------

        if timeout is None:
            raise InvalidOfferState(
                "Offer timeout is required."
            )

        try:
            timeout = int(timeout)
        except (TypeError, ValueError):
            raise InvalidOfferState(
                "Offer timeout must be a valid integer."
            )

        if timeout <= 0:
            raise InvalidOfferState(
                "Offer timeout must be greater than zero."
            )

        # ------------------------------------------
        # Validate radius
        # ------------------------------------------

        if radius is None:
            raise InvalidOfferState(
                "Search radius is required."
            )

        try:
            radius = Decimal(str(radius))
        except (InvalidOperation, TypeError, ValueError):
            raise InvalidOfferState(
                "Search radius must be a valid number."
            )

        if radius <= 0:
            raise InvalidOfferState(
                "Search radius must be greater than zero."
            )

        # ------------------------------------------
        # Lock delivery
        # ------------------------------------------

        delivery = (
            Delivery.objects
            .select_for_update()
            .get(
                pk=delivery.pk,
            )
        )

        # ------------------------------------------
        # Validate delivery
        # ------------------------------------------

        cls._validate_delivery(
            delivery,
        )

        # ------------------------------------------
        # Prevent duplicate pending offer
        # ------------------------------------------

        existing_offer = (
            DeliveryOffer.objects
            .filter(
                delivery_id=delivery.pk,
                rider_id=rider.pk,
                status=DeliveryOffer.Status.PENDING,
            )
            .first()
        )

        if existing_offer:
            raise InvalidOfferState(
                "This rider already has a pending "
                "offer for this delivery."
            )

        # ------------------------------------------
        # Calculate expiration
        # ------------------------------------------

        now = timezone.now()

        expires_at = (
            now
            + timedelta(
                seconds=timeout,
            )
        )

        # ------------------------------------------
        # Create offer
        # ------------------------------------------

        return DeliveryOffer.objects.create(
            delivery=delivery,
            rider=rider,
            search_radius=radius,
            expires_at=expires_at,
            status=DeliveryOffer.Status.PENDING,
        )

    # ==================================================
    # Accept
    # ==================================================

    @classmethod
    @transaction.atomic
    def accept(
        cls,
        offer,
    ):
        """
        Accept a pending delivery offer.

        This method owns ONLY the offer lifecycle.

        It does NOT create a DeliveryAssignment.

        Assignment creation belongs to
        AssignmentService.

        Competing pending offers for the same delivery
        are cancelled after this offer is accepted.
        """

        # ------------------------------------------
        # Lock offer
        # ------------------------------------------

        offer = cls._lock_offer(
            offer,
        )

        # ------------------------------------------
        # Validate pending
        # ------------------------------------------

        cls._validate_actionable(
            offer,
            action="accept",
        )

        # ------------------------------------------
        # Accept
        # ------------------------------------------

        now = timezone.now()

        offer.status = (
            DeliveryOffer.Status.ACCEPTED
        )

        offer.responded_at = now

        offer.save(
            update_fields=[
                "status",
                "responded_at",
            ],
        )

        # ------------------------------------------
        # Cancel competing offers
        # ------------------------------------------

        (
            DeliveryOffer.objects
            .filter(
                delivery_id=offer.delivery_id,
                status=DeliveryOffer.Status.PENDING,
            )
            .exclude(
                pk=offer.pk,
            )
            .update(
                status=DeliveryOffer.Status.CANCELLED,
                responded_at=now,
            )
        )

        return offer

    # ==================================================
    # Reject
    # ==================================================

    @classmethod
    @transaction.atomic
    def reject(
        cls,
        offer,
        reason="",
    ):
        """
        Reject a pending delivery offer.

        An expired offer cannot be rejected.
        """

        # ------------------------------------------
        # Lock offer
        # ------------------------------------------

        offer = cls._lock_offer(
            offer,
        )

        # ------------------------------------------
        # Validate actionable state
        # ------------------------------------------

        cls._validate_actionable(
            offer,
            action="reject",
        )

        # ------------------------------------------
        # Reject
        # ------------------------------------------

        cls._update_status(
            offer=offer,
            status=DeliveryOffer.Status.REJECTED,
            rejection_reason=reason,
        )

        return offer

    # ==================================================
    # Expire
    # ==================================================

    @classmethod
    @transaction.atomic
    def expire(
        cls,
        offer,
    ):
        """
        Expire a pending delivery offer.

        IMPORTANT
        ---------
        Unlike accept/reject/cancel, expiration requires
        the offer to already be past expires_at.

        Therefore an expired PENDING offer is a valid
        candidate for this method.
        """

        # ------------------------------------------
        # Lock offer
        # ------------------------------------------

        offer = cls._lock_offer(
            offer,
        )

        # ------------------------------------------
        # Validate state
        # ------------------------------------------

        if offer.status != DeliveryOffer.Status.PENDING:
            raise InvalidOfferState(
                f"Offer with status "
                f"'{offer.status}' cannot be expired."
            )

        # ------------------------------------------
        # Validate expiration timestamp
        # ------------------------------------------

        if offer.expires_at is None:
            raise InvalidOfferState(
                "This delivery offer has no "
                "expiration time."
            )

        # ------------------------------------------
        # Ensure offer actually expired
        # ------------------------------------------

        now = timezone.now()

        if offer.expires_at > now:
            raise InvalidOfferState(
                "This delivery offer has not "
                "expired yet."
            )

        # ------------------------------------------
        # Expire
        # ------------------------------------------

        cls._update_status(
            offer=offer,
            status=DeliveryOffer.Status.EXPIRED,
        )

        return offer

    # ==================================================
    # Cancel
    # ==================================================

    @classmethod
    @transaction.atomic
    def cancel(
        cls,
        offer,
    ):
        """
        Cancel a pending delivery offer.

        Cancellation is intentionally separate from
        expiration and rejection.

        An offer can only be cancelled while it is
        still actionable.
        """

        # ------------------------------------------
        # Lock offer
        # ------------------------------------------

        offer = cls._lock_offer(
            offer,
        )

        # ------------------------------------------
        # Validate actionable state
        # ------------------------------------------

        cls._validate_actionable(
            offer,
            action="cancel",
        )

        # ------------------------------------------
        # Cancel
        # ------------------------------------------

        cls._update_status(
            offer=offer,
            status=DeliveryOffer.Status.CANCELLED,
        )

        return offer

    # ==================================================
    # Lock Offer
    # ==================================================

    @staticmethod
    def _lock_offer(
        offer,
    ):
        """
        Lock the offer row before changing its state.

        This protects against concurrent operations such
        as:

            ACCEPT + REJECT
            ACCEPT + EXPIRE
            REJECT + EXPIRE
            CANCEL + ACCEPT

        The database row lock ensures that only one
        transaction can transition the offer at a time.
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

    # ==================================================
    # Validate Actionable Offer
    # ==================================================

    @staticmethod
    def _validate_actionable(
        offer,
        action,
    ):
        """
        Validate whether a pending offer can perform
        an interactive rider action.

        Interactive actions:

            • accept
            • reject
            • cancel

        Expiration is handled separately by expire().
        """

        if offer.status != DeliveryOffer.Status.PENDING:

            raise InvalidOfferState(
                f"Offer with status "
                f"'{offer.status}' cannot be "
                f"{action}ed."
            )

        # ------------------------------------------
        # Expiration timestamp
        # ------------------------------------------

        if offer.expires_at is None:

            raise InvalidOfferState(
                "This delivery offer has no "
                "expiration time."
            )

        # ------------------------------------------
        # Expiration validation
        # ------------------------------------------

        if offer.expires_at <= timezone.now():

            raise InvalidOfferState(
                "This delivery offer has expired."
            )

    # ==================================================
    # Update Status
    # ==================================================

    @staticmethod
    def _update_status(
        offer,
        status,
        **extra_fields,
    ):
        """
        Update offer lifecycle state.

        responded_at records the time at which the
        offer leaves PENDING state.

        Additional lifecycle fields can be supplied,
        such as rejection_reason.
        """

        if offer is None:
            raise InvalidOfferState(
                "Delivery offer is required."
            )

        if status == DeliveryOffer.Status.PENDING:
            raise InvalidOfferState(
                "Lifecycle update cannot transition "
                "an offer back to PENDING."
            )

        now = timezone.now()

        offer.status = status
        offer.responded_at = now

        update_fields = [
            "status",
            "responded_at",
        ]

        for field_name, value in extra_fields.items():

            setattr(
                offer,
                field_name,
                value,
            )

            update_fields.append(
                field_name,
            )

        offer.save(
            update_fields=update_fields,
        )

        return offer

    # ==================================================
    # Validate Delivery
    # ==================================================

    @staticmethod
    def _validate_delivery(
        delivery,
    ):
        """
        Ensure the delivery is still eligible to
        receive a rider offer.

        Terminal states:

            DELIVERED
            CANCELLED

        A delivery with an existing rider assignment
        cannot receive another offer.
        """

        if delivery is None:

            raise InvalidOfferState(
                "Delivery is required."
            )

        # ------------------------------------------
        # Terminal states
        # ------------------------------------------

        terminal_statuses = {
            Delivery.DeliveryStatus.DELIVERED,
            Delivery.DeliveryStatus.CANCELLED,
        }

        if delivery.status in terminal_statuses:

            raise InvalidOfferState(
                "Cannot create an offer for a "
                "terminal delivery."
            )

        # ------------------------------------------
        # Existing rider assignment
        # ------------------------------------------

        if getattr(
            delivery,
            "rider_id",
            None,
        ):

            raise InvalidOfferState(
                "Delivery already has a rider assigned."
            )