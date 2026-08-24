from django.conf import settings
from django.db import models
from common.models import TimeStampedModel


class DispatchHistory(TimeStampedModel):
    """
    Immutable audit trail for the dispatch lifecycle.

    Every important dispatch transition should create
    one history record.
    """

    class EventType(models.TextChoices):
        DELIVERY_CREATED = (
            "DELIVERY_CREATED",
            "Delivery Created",
        )
        DISPATCH_STARTED = (
            "DISPATCH_STARTED",
            "Dispatch Started",
        )
        OFFER_CREATED = (
            "OFFER_CREATED",
            "Offer Created",
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
        OFFER_CANCELLED = (
            "OFFER_CANCELLED",
            "Offer Cancelled",
        )
        RIDER_ASSIGNED = (
            "RIDER_ASSIGNED",
            "Rider Assigned",
        )
        ASSIGNMENT_ACCEPTED = (
            "ASSIGNMENT_ACCEPTED",
            "Assignment Accepted",
        )
        PICKUP_STARTED = (
            "PICKUP_STARTED",
            "Pickup Started",
        )
        ARRIVED_PICKUP = (
            "ARRIVED_PICKUP",
            "Arrived Pickup",
        )
        PICKUP_COMPLETED = (
            "PICKUP_COMPLETED",
            "Pickup Completed",
        )
        DELIVERY_STARTED = (
            "DELIVERY_STARTED",
            "Delivery Started",
        )
        ARRIVED_DESTINATION = (
            "ARRIVED_DESTINATION",
            "Arrived Destination",
        )
        DELIVERY_COMPLETED = (
            "DELIVERY_COMPLETED",
            "Delivery Completed",
        )
        ASSIGNMENT_CANCELLED = (
            "ASSIGNMENT_CANCELLED",
            "Assignment Cancelled",
        )
        ASSIGNMENT_REASSIGNED = (
            "ASSIGNMENT_REASSIGNED",
            "Assignment Reassigned",
        )
        DISPATCH_FAILED = (
            "DISPATCH_FAILED",
            "Dispatch Failed",
        )

    delivery = models.ForeignKey(
        "deliveries.Delivery",
        on_delete=models.CASCADE,
        related_name="dispatch_history",
    )

    assignment = models.ForeignKey(
        "deliveries.DeliveryAssignment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_history",
    )

    offer = models.ForeignKey(
        "deliveries.DeliveryOffer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_history",
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_history",
    )

    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
    )

    status = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )

    message = models.TextField(
        blank=True,
        default="",
    )

    reason = models.TextField(
        blank=True,
        default="",
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ("created_at",)

        indexes = [
            models.Index(
                fields=[
                    "delivery",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "event_type",
                    "created_at",
                ]
            ),
            models.Index(
                fields=[
                    "rider",
                    "created_at",
                ]
            ),
        ]

    def __str__(self):
        return (
            f"{self.delivery} - "
            f"{self.event_type}"
        )