from django.apps import AppConfig


class deliveries(AppConfig):

    default_auto_field = (
        "django.db.models.BigAutoField"
    )

    name = "deliveries"

    def ready(self):

        from .dispatch.events import (
            DeliveryOfferAcceptedEvent,
            DeliveryOfferRejectedEvent,
        )

        from .dispatch.listeners import (
            notify_customer_offer_accepted,
            notify_vendor_offer_accepted,
            notify_rider_offer_rejected,
        )

        from .dispatch.publisher import (
            EventPublisher,
        )

        EventPublisher.subscribe(
            DeliveryOfferAcceptedEvent,
            notify_customer_offer_accepted,
        )

        EventPublisher.subscribe(
            DeliveryOfferAcceptedEvent,
            notify_vendor_offer_accepted,
        )

        EventPublisher.subscribe(
            DeliveryOfferRejectedEvent,
            notify_rider_offer_rejected,
        )