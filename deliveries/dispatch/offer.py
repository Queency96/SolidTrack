from datetime import timedelta
from django.utils import timezone
from deliveries.models import DeliveryOffer


class DeliveryOfferService:
    @staticmethod
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