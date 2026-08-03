from deliveries.models import (
    DeliveryTimeline,
)


class DeliveryTimelineService:
    @staticmethod
    def log(
        delivery,
        event,
        title,
        description="",
        rider=None,
        created_by=None,
        metadata=None,
    ):

        return DeliveryTimeline.objects.create(
            delivery=delivery,
            rider=rider,
            event=event,
            title=title,
            description=description,
            created_by=created_by,
            metadata=metadata or {},
        )