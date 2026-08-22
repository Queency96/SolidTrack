from datetime import timedelta
from decimal import Decimal

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
        # Validate timeout
        # ------------------------------------------

        if timeout is None:

            raise InvalidOfferState(
                "Offer timeout is required."
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

        radius = Decimal(
            str(radius)
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
        # Validate delivery state
        # ------------------------------------------

        cls._validate_delivery(
            delivery,
        )

        # ------------------------------------------
        # Validate rider
        # ------------------------------------------

        if rider is None:

            raise InvalidOfferState(
                "Rider is required to create an offer."
            )

        # ------------------------------------------
        # Prevent duplicate pending offer
        # ------------------------------------------

        existing_offer = (
            DeliveryOffer.objects
            .select_for_update()
            .filter(
                delivery=delivery,
                rider=rider,
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

        # ------------------------------------------
        # Calculate expiration
        # ------------------------------------------

        expires_at = (
            timezone.now()
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
            status=(
                DeliveryOffer.Status.PENDING
            ),
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

        This method only changes the offer state.

        Assignment creation is handled separately by
        AssignmentService.
        """

        offer = cls._lock_offer(
            offer,
        )

        cls._validate_pending(
            offer,
        )

        cls._update_status(
            offer,
            DeliveryOffer.Status.ACCEPTED,
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
        """

        offer = cls._lock_offer(
            offer,
        )

        cls._validate_pending(
            offer,
        )

        cls._update_status(
            offer,
            DeliveryOffer.Status.REJECTED,
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
        Explicitly expire a pending offer.

        The offer must actually be past its expiration
        timestamp.
        """

        offer = cls._lock_offer(
            offer,
        )

        cls._validate_pending(
            offer,
        )

        now = timezone.now()

        if offer.expires_at is None:

            raise InvalidOfferState(
                "This delivery offer has no "
                "expiration time."
            )

        if offer.expires_at > now:

            raise InvalidOfferState(
                "This delivery offer has not "
                "expired yet."
            )

        cls._update_status(
            offer,
            DeliveryOffer.Status.EXPIRED,
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
        """

        offer = cls._lock_offer(
            offer,
        )

        cls._validate_pending(
            offer,
        )

        cls._update_status(
            offer,
            DeliveryOffer.Status.CANCELLED,
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

        This protects against concurrent rider
        responses such as:

            ACCEPT + REJECT
            ACCEPT + EXPIRE
            REJECT + EXPIRE
        """

        if offer is None:

            raise InvalidOfferState(
                "Delivery offer is required."
            )

        return (
            DeliveryOffer.objects
            .select_for_update()
            .select_related(
                "delivery",
                "rider",
            )
            .get(
                pk=offer.pk,
            )
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
        Update offer status and response timestamp.

        Additional fields can be supplied for lifecycle
        information such as rejection_reason.
        """

        offer.status = status
        offer.responded_at = timezone.now()

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
    # Validate Pending
    # ==================================================

    @staticmethod
    def _validate_pending(
        offer,
    ):
        """
        Ensure the offer is still actionable.

        Only PENDING offers can be accepted,
        rejected, expired, or cancelled.

        An expired pending offer cannot be silently
        converted into another state.
        """

        if (
            offer.status
            != DeliveryOffer.Status.PENDING
        ):

            raise InvalidOfferState(
                "Only pending offers can be updated."
            )

        if offer.expires_at is None:

            raise InvalidOfferState(
                "This delivery offer has no "
                "expiration time."
            )

        if (
            offer.expires_at
            <= timezone.now()
        ):

            raise InvalidOfferState(
                "This delivery offer has expired."
            )

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
        """

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
        # Prevent offering after assignment
        # ------------------------------------------

        if getattr(
            delivery,
            "rider_id",
            None,
        ):

            raise InvalidOfferState(
                "Delivery already has a rider assigned."
            )