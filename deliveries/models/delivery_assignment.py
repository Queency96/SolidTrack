from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from .delivery import Delivery


class DeliveryAssignment(TimeStampedModel):
    class AssignmentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        ACCEPTED = "ACCEPTED", "Accepted"
        EN_ROUTE_PICKUP = "EN_ROUTE_PICKUP", "En Route to Pickup"
        ARRIVED_PICKUP = "ARRIVED_PICKUP", "Arrived at Pickup"
        PICKED_UP = "PICKED_UP", "Picked Up"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        ARRIVED_DESTINATION = (
            "ARRIVED_DESTINATION",
            "Arrived at Destination",
        )
        COMPLETED = "COMPLETED", "Completed"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    is_active = models.BooleanField(
        default=True,
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="delivery_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_deliveries",
        help_text="Admin or system that assigned the rider.",
    )

    status = models.CharField(
        max_length=30,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.PENDING,
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejected_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    cancellation_reason = models.TextField(
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-assigned_at"]

        indexes = [
            models.Index(
                fields=["delivery", "status"],
            ),
            models.Index(
                fields=["rider", "status"],
            ),
            models.Index(
                fields=["status"],
            ),
            models.Index(
                fields=["assigned_at"],
            ),
            models.Index(
                fields=["is_active"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.delivery.tracking_number} "
            f"→ {self.rider.get_full_name() or self.rider.email}"
        )