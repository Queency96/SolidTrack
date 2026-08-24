from django.utils import timezone
import uuid
from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from decimal import Decimal
from riders.models import RiderProfile

class DeliveryOffer(TimeStampedModel):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    # ==================================================
    # Relationships
    # ==================================================

    delivery = models.ForeignKey(
        "Delivery",
        on_delete=models.CASCADE,
        related_name="offers",
    )

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="delivery_offers",
    )

    # ==================================================
    # Offer State
    # ==================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # ==================================================
    # Dispatch Information
    # ==================================================

    search_radius = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    # ==================================================
    # Timestamps
    # ==================================================

    offered_at = models.DateTimeField(
        auto_now_add=True,
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    expires_at = models.DateTimeField()

    # ==================================================
    # Response
    # ==================================================

    rejection_reason = models.TextField(
        blank=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:
        ordering = (
            "-offered_at",
        )

        indexes = [
            models.Index(
                fields=[
                    "delivery",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "rider",
                    "status",
                ],
            ),
            models.Index(
                fields=[
                    "expires_at",
                ],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):
        rider_name = (
            self.rider.get_full_name()
            or self.rider.email
        )

        return (
            f"{self.delivery.tracking_number} → "
            f"{rider_name}"
        )