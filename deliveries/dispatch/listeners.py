from .events import (
    DeliveryOfferAcceptedEvent,
    DeliveryOfferRejectedEvent,
)
from .notifier import DispatchNotifier
from deliveries.models import DeliveryTimeline
from .timeline import (
    DeliveryTimelineService,
)


def notify_customer_offer_accepted(
    event,
):

    DispatchNotifier.notify_customer(
        event.assignment
    )


def notify_vendor_offer_accepted(
    event,
):

    DispatchNotifier.notify_vendor(
        event.assignment
    )


def notify_rider_offer_rejected(
    event,
):

    DispatchNotifier.notify_rejection(
        event.offer
    )





def log_offer_accepted(
    event,
):

    DeliveryTimelineService.log(
        delivery=event.assignment.delivery,
        rider=event.assignment.rider,
        event=DeliveryTimeline.EventType.ASSIGNED,
        title="Rider Assigned",
        description=(
            "Delivery accepted by rider."
        ),
    )



def log_offer_rejected(
    event,
):

    DeliveryTimelineService.log(
        delivery=event.offer.delivery,
        rider=event.offer.rider,
        event=DeliveryTimeline.EventType.OFFER_REJECTED,
        title="Offer Rejected",
        description=(
            "Rider rejected delivery."
        ),
    )