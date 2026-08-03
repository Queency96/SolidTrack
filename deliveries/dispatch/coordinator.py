from .context import DispatchContext
from deliveries.constants import (
    DeliveryOfferAction,
)
from .events import (
    DeliveryCreatedEvent,
    DeliveryOfferAcceptedEvent,
    DeliveryOfferRejectedEvent,
    DeliveryOfferExpiredEvent,
)
from .offer import DeliveryOfferService
from .pipeline import DispatchPipeline
from .publisher import EventPublisher
from .result import DispatchResult
from .service import DispatchConfigurationService
from .status import DispatchStatus


class DispatchCoordinator:
    """
    Coordinates the complete dispatch lifecycle.

    Responsibilities
    ----------------
    • Delivery creation
    • Rider dispatch
    • Rider responses
    • Offer expiration
    • Event publishing
    """

    # ==================================================
    # Delivery Created
    # ==================================================

    @classmethod
    def delivery_created(
        cls,
        delivery,
    ):
        EventPublisher.publish(
            DeliveryCreatedEvent(
                delivery=delivery,
            )
        )

        return cls.dispatch(
            delivery,
        )

    # ==================================================
    # Dispatch Delivery
    # ==================================================

    @classmethod
    def dispatch(
        cls,
        delivery,
    ):
        context = DispatchContext(
            delivery=delivery,
            config=(
                DispatchConfigurationService
                .get_configuration()
            ),
            customer=getattr(
                delivery,
                "customer",
                None,
            ),
            vendor=getattr(
                delivery,
                "vendor",
                None,
            ),
        )

        pipeline = DispatchPipeline(
            context=context,
        )

        return pipeline.run()

    # ==================================================
    # Rider Response
    # ==================================================

    @classmethod
    def respond_to_offer(
        cls,
        offer,
        action,
        reason="",
    ):
        if action == DeliveryOfferAction.ACCEPT:
            return cls._accept_offer(
                offer,
            )

        if action == DeliveryOfferAction.REJECT:
            return cls._reject_offer(
                offer,
                reason,
            )

        return DispatchResult.failure_result(
            status=DispatchStatus.FAILED,
            message="Invalid dispatch action.",
            delivery=offer.delivery,
        )

    # ==================================================
    # Accept Offer
    # ==================================================

    @classmethod
    def _accept_offer(
        cls,
        offer,
    ):
        assignment = (
            DeliveryOfferService.accept(
                offer,
            )
        )

        EventPublisher.publish(
            DeliveryOfferAcceptedEvent(
                assignment=assignment,
            )
        )

        return DispatchResult.success_result(
            status=DispatchStatus.ACCEPTED,
            message="Delivery offer accepted.",
            delivery=offer.delivery,
            assignment=assignment,
            offer=offer,
        )

    # ==================================================
    # Reject Offer
    # ==================================================

    @classmethod
    def _reject_offer(
        cls,
        offer,
        reason,
    ):
        rejected_offer = (
            DeliveryOfferService.reject(
                offer,
                reason,
            )
        )

        EventPublisher.publish(
            DeliveryOfferRejectedEvent(
                offer=rejected_offer,
            )
        )

        redispatch_result = cls.dispatch(
            rejected_offer.delivery,
        )

        redispatch_result.offer = (
            rejected_offer
        )

        redispatch_result.add_warning(
            "Previous rider rejected the offer."
        )

        return redispatch_result

    # ==================================================
    # Offer Expired
    # ==================================================

    @classmethod
    def offer_expired(
        cls,
        offer,
    ):
        expired_offer = (
            DeliveryOfferService.expire(
                offer,
            )
        )

        EventPublisher.publish(
            DeliveryOfferExpiredEvent(
                offer=expired_offer,
            )
        )

        redispatch_result = cls.dispatch(
            expired_offer.delivery,
        )

        redispatch_result.offer = (
            expired_offer
        )

        redispatch_result.add_warning(
            "Previous rider offer expired."
        )

        return redispatch_result