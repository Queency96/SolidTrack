from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from deliveries.models import DeliveryOffer

from .exceptions import InvalidOfferState


class DeliveryOfferService:
    """
    Handles the lifecycle of delivery offers.

    Responsibilities
    ----------------
    • Create offers
    • Accept offers
    • Reject offers
    • Expire offers
    • Cancel offers

    This service DOES NOT create assignments or
    trigger redispatching.
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
        return DeliveryOffer.objects.create(
            delivery=delivery,
            rider=rider,
            search_radius=radius,
            expires_at=(
                timezone.now()
                + timedelta(seconds=timeout)
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

        cls._cancel_other_offers(
            offer,
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
        offer = cls._lock_offer(
            offer,
        )

        cls._validate_pending(
            offer,
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
    # Cancel Remaining Offers
    # ==================================================

    @classmethod
    def _cancel_other_offers(
        cls,
        accepted_offer,
    ):
        DeliveryOffer.objects.filter(
            delivery=accepted_offer.delivery,
            status=DeliveryOffer.Status.PENDING,
        ).exclude(
            pk=accepted_offer.pk,
        ).update(
            status=DeliveryOffer.Status.CANCELLED,
            responded_at=timezone.now(),
        )

    # ==================================================
    # Lock
    # ==================================================

    @staticmethod
    def _lock_offer(
        offer,
    ):
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
        offer.status = status

        update_fields = [
            "status",
            "responded_at",
        ]

        offer.responded_at = (
            timezone.now()
        )

        for field, value in extra_fields.items():
            setattr(
                offer,
                field,
                value,
            )
            update_fields.append(
                field,
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
        if (
            offer.status
            != DeliveryOffer.Status.PENDING
        ):
            raise InvalidOfferState(
                "Only pending offers can be updated."
            )

        if offer.expires_at <= timezone.now():
            raise InvalidOfferState(
                "This delivery offer has expired."
            )