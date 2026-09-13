from celery import shared_task
from deliveries.models import DeliveryOffer
from .coordinator import DispatchCoordinator


@shared_task(
    bind=True,
    max_retries=3,
)
def expire_delivery_offer(
    self,
    offer_id,
):

    try:

        offer = (
            DeliveryOffer.objects
            .select_related(
                "delivery",
                "rider",
            )
            .get(
                pk=offer_id,
            )
        )

    except DeliveryOffer.DoesNotExist:
        return

    if (
        offer.status
        != DeliveryOffer.Status.PENDING
    ):
        return

    DispatchCoordinator.offer_expired(
        offer
    )