from django.utils import timezone
from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from .delivery import Delivery
import uuid


class DeliveryTimeline(TimeStampedModel):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        SEARCHING_RIDERS = (
            "SEARCHING_RIDERS",
            "Searching Riders",
        )
        OFFER_SENT = (
            "OFFER_SENT",
            "Offer Sent",
        )
        OFFER_ACCEPTED = (
            "OFFER_ACCEPTED",
            "Offer Accepted",
        )
        OFFER_REJECTED = (
            "OFFER_REJECTED",
            "Offer Rejected",
        )
        OFFER_EXPIRED = (
            "OFFER_EXPIRED",
            "Offer Expired",
        )
        ASSIGNED = (
            "ASSIGNED",
            "Assigned",
        )
        RIDER_ARRIVED = (
            "RIDER_ARRIVED",
            "Rider Arrived",
        )
        PICKED_UP = (
            "PICKED_UP",
            "Picked Up",
        )
        IN_TRANSIT = (
            "IN_TRANSIT",
            "In Transit",
        )
        DELIVERED = (
            "DELIVERED",
            "Delivered",
        )
        CANCELLED = (
            "CANCELLED",
            "Cancelled",
        )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="timeline",
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    event = models.CharField(
        max_length=50,
        choices=EventType.choices,
    )

    title = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    occurred_at = models.DateTimeField(
        default=timezone.now,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="delivery_timeline_events",
    )
    class Meta:
        ordering = [
            "-occurred_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "delivery",
                    "occurred_at",
                ]
            ),
        ]
    def __str__(self):
        return (
            f"{self.delivery.tracking_number}"
            f" - {self.title}"
        )






# class AssignmentAction(models.TextChoices):

#     ACCEPT = "accept", "Accept"

#     START_PICKUP = (
#         "start_pickup",
#         "Start Pickup",
#     )

#     ARRIVE_PICKUP = (
#         "arrive_pickup",
#         "Arrive Pickup",
#     )

#     PICKUP_COMPLETED = (
#         "pickup_completed",
#         "Pickup Completed",
#     )

#     START_DELIVERY = (
#         "start_delivery",
#         "Start Delivery",
#     )

#     ARRIVE_DESTINATION = (
#         "arrive_destination",
#         "Arrive Destination",
#     )

#     COMPLETE = (
#         "complete",
#         "Complete",
#     )

#     CANCEL = (
#         "cancel",
#         "Cancel",
#     )

#     REASSIGN = (
#         "reassign",
#         "Reassign",
#     )


