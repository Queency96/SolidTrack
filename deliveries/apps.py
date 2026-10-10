from django.apps import AppConfig


class deliveries(AppConfig):

    default_auto_field = (
        "django.db.models.BigAutoField"
    )

    name = "deliveries"

    def ready(self):

        # Cache invalidation signals
        import deliveries.signals  # noqa: F401

        # Event subscribers
        from .dispatch.events import (
            DeliveryAssignedEvent,
            DeliveryOfferExpiredEvent,
            DeliveryOfferRejectedEvent,
        )

        from .dispatch.listeners import (
            log_offer_accepted,
            log_offer_expired,
            log_offer_rejected,
            notify_customer_offer_accepted,
            notify_vendor_offer_accepted,
            notify_rider_offer_rejected,
        )

        from .dispatch.publisher import EventPublisher

        # ------------------------------------------------
        # Assignment succeeded
        # ------------------------------------------------

        EventPublisher.subscribe(
            DeliveryAssignedEvent,
            notify_customer_offer_accepted,
        )

        EventPublisher.subscribe(
            DeliveryAssignedEvent,
            notify_vendor_offer_accepted,
        )

        EventPublisher.subscribe(
            DeliveryAssignedEvent,
            log_offer_accepted,
        )

        # ------------------------------------------------
        # Offer rejected
        # ------------------------------------------------

        EventPublisher.subscribe(
            DeliveryOfferRejectedEvent,
            notify_rider_offer_rejected,
        )

        EventPublisher.subscribe(
            DeliveryOfferRejectedEvent,
            log_offer_rejected,
        )

        # ------------------------------------------------
        # Offer expired
        # ------------------------------------------------

        EventPublisher.subscribe(
            DeliveryOfferExpiredEvent,
            log_offer_expired,
        )