from datetime import timedelta
from deliveries.constants import DeliveryOfferAction
from django.db import transaction
from django.utils import timezone
from deliveries.models import DeliveryOffer
from .assignment import AssignmentService
from .exceptions import InvalidOfferState


class DeliveryOfferService:

    # ------------------------------------------
    # Create Offer
    # ------------------------------------------
    @staticmethod
    @transaction.atomic
    def create_offer(
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

    # ------------------------------------------
    # Public Response Entry Point
    # ------------------------------------------
    @staticmethod
    @transaction.atomic
    def respond(
        offer,
        action,
        reason="",
    ):

        offer = (
            DeliveryOffer.objects
            .select_for_update()
            .get(pk=offer.pk)
        )

        if action == DeliveryOfferAction.ACCEPT:
            return DeliveryOfferService.accept(
                offer
            )

        if action == DeliveryOfferAction.REJECT:
            return DeliveryOfferService.reject(
                offer,
                reason,
            )

        raise InvalidOfferState(
            "Invalid offer action."
        )

    # ------------------------------------------
    # Accept
    # ------------------------------------------
    @staticmethod
    def accept(
        offer,
    ):
        DeliveryOfferService._validate_pending(
            offer
        )
        DeliveryOfferService._update_status(
            offer,
            DeliveryOffer.Status.ACCEPTED,
        )
        DeliveryOfferService._cancel_other_offers(
            offer
        )
        return AssignmentService.assign(
            delivery=offer.delivery,
            rider=offer.rider,
        )

    # ------------------------------------------
    # Reject
    # ------------------------------------------
    @staticmethod
    def reject(
        offer,
        reason="",
    ):
        DeliveryOfferService._validate_pending(
            offer
        )
        offer.rejection_reason = reason

        DeliveryOfferService._update_status(
            offer,
            DeliveryOffer.Status.REJECTED,
            save_reason=True,
        )
        return offer

    # ------------------------------------------
    # Expire
    # ------------------------------------------
    @staticmethod
    def expire(
        offer,
    ):
        DeliveryOfferService._validate_pending(
            offer
        )
        DeliveryOfferService._update_status(
            offer,
            DeliveryOffer.Status.EXPIRED,
        )
        return offer

    # ------------------------------------------
    # Cancel Remaining Offers
    # ------------------------------------------
    @staticmethod
    def _cancel_other_offers(
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

    # ------------------------------------------
    # Update Status
    # ------------------------------------------
    @staticmethod
    def _update_status(
        offer,
        status,
        save_reason=False,
    ):
        offer.status = status
        offer.responded_at = timezone.now()
        fields = [
            "status",
            "responded_at",
        ]
        if save_reason:
            fields.append(
                "rejection_reason"
            )
        offer.save(
            update_fields=fields,
        )

    # ------------------------------------------
    # Validation
    # ------------------------------------------
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