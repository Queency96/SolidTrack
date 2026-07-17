from deliveries.constants import DeliveryOfferAction

from .offer import DeliveryOfferService
from .pipeline import DispatchPipeline
from .notifier import DispatchNotifier


class DispatchCoordinator:

    @classmethod
    def respond_to_offer(
        cls,
        offer,
        action,
        reason="",
    ):

        if action == DeliveryOfferAction.ACCEPT:
            return cls._accept_offer(
                offer
            )

        if action == DeliveryOfferAction.REJECT:
            return cls._reject_offer(
                offer,
                reason,
            )

        raise ValueError(
            "Invalid dispatch action."
        )

    # ----------------------------------

    @classmethod
    def _accept_offer(
        cls,
        offer,
    ):

        assignment = (
            DeliveryOfferService.accept(
                offer
            )
        )

        DispatchNotifier.notify_customer(
            assignment
        )

        DispatchNotifier.notify_vendor(
            assignment
        )

        DispatchNotifier.notify_rider(
            assignment
        )

        return {
            "status": "accepted",
            "assignment": assignment,
        }

    # ----------------------------------

    @classmethod
    def _reject_offer(
        cls,
        offer,
        reason,
    ):

        DeliveryOfferService.reject(
            offer,
            reason,
        )

        pipeline = DispatchPipeline(
            offer.delivery
        )

        pipeline.run()

        return {
            "status": "rejected",
        }