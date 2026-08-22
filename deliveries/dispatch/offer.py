from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from deliveries.models import DeliveryOffer

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

        A rider cannot have multiple active offers
        for the same delivery.
        """

        # ------------------------------------------
        # Validate timeout
        # ------------------------------------------

        if timeout <= 0:
            raise InvalidOfferState(
                "Offer timeout must be greater than zero."
            )

        # ------------------------------------------
        # Validate radius
        # ------------------------------------------

        if radius <= 0:
            raise InvalidOfferState(
                "Search radius must be greater than zero."
            )

        # ------------------------------------------
        # Lock delivery
        # ------------------------------------------

        from deliveries.models import Delivery

        delivery = (
            Delivery.objects
            .select_for_update()
            .get(pk=delivery.pk)
        )

        # ------------------------------------------
        # Prevent duplicate active offer
        # ------------------------------------------

        existing_offer = (
            DeliveryOffer.objects
            .select_for_update()
            .filter(
                delivery=delivery,
                rider=rider,
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
        # Create offer
        # ------------------------------------------

        expires_at = (
            timezone.now()
            + timedelta(
                seconds=timeout,
            )
        )

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

        if offer.expires_at > now:
            raise InvalidOfferState(
                "This delivery offer has not expired yet."
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

        This protects against concurrent rider responses.
        """

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
    # Validation
    # ==================================================

    @staticmethod
    def _validate_pending(
        offer,
    ):
        """
        Ensure the offer is still actionable.

        Expired offers are rejected rather than silently
        changing state here. Explicit expiration remains
        the responsibility of expire().
        """

        if (
            offer.status
            != DeliveryOffer.Status.PENDING
        ):
            raise InvalidOfferState(
                "Only pending offers can be updated."
            )

        if (
            offer.expires_at
            <= timezone.now()
        ):
            raise InvalidOfferState(
                "This delivery offer has expired."
            )