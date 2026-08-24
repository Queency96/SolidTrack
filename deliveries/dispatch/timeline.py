from deliveries.models.dispatch_history import (
    DispatchHistory,
)



class DeliveryTimelineService:
    """
    Read-only service for retrieving the chronological
    dispatch timeline of a delivery.
    """

    @classmethod
    def get_timeline(
        cls,
        delivery,
    ):
        history = (
            DispatchHistory.objects
            .filter(
                delivery=delivery,
            )
            .select_related(
                "rider",
                "offer",
                "assignment",
            )
            .order_by(
                "created_at",
            )
        )

        return [
            cls._serialize_event(event)
            for event in history
        ]

    @staticmethod
    def _serialize_event(
        event,
    ):
        return {
            "id": event.id,
            "event_type": event.event_type,
            "status": event.status,
            "message": event.message,
            "reason": event.reason,
            "timestamp": event.created_at,

            "delivery_id": (
                event.delivery_id
            ),

            "offer_id": (
                event.offer_id
            ),

            "assignment_id": (
                event.assignment_id
            ),

            "rider_id": (
                event.rider_id
            ),

            "metadata": event.metadata,
        }