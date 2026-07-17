from deliveries.services import NotificationService

class DispatchNotifier:
    @staticmethod
    def offer_delivery(offer):
        NotificationService.create_notification(
            user=offer.rider,
            title="New Delivery",
            message=(
                f"You have a new delivery request."
            ),
            notification_type="DELIVERY_OFFER",
            data={
                "offer_id": offer.id,
                "delivery_id": offer.delivery.id,
            },
        )