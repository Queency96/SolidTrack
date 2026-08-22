from django.db import models
from django.conf import settings
from common.models import TimeStampedModel
import uuid


import uuid

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class RiderProfile(TimeStampedModel):

    class VehicleType(models.TextChoices):
        BIKE = "BIKE", "Bike"
        CAR = "CAR", "Car"
        VAN = "VAN", "Van"

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rider_profile",
    )

    # ==================================================
    # Vehicle
    # ==================================================

    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices,
    )

    vehicle_plate_number = models.CharField(
        max_length=30,
    )

    # ==================================================
    # Verification
    # ==================================================

    driver_license = models.ImageField(
        upload_to="riders/licenses/",
    )

    nin = models.CharField(
        max_length=20,
    )

    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_riders",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    rejection_reason = models.TextField(
        blank=True,
    )

    # ==================================================
    # Availability
    # ==================================================

    is_online = models.BooleanField(
        default=False,
    )

    is_available = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Rating
    # ==================================================

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "is_online",
                    "is_available",
                ]
            ),
            models.Index(
                fields=[
                    "verification_status",
                ]
            ),
            models.Index(
                fields=[
                    "vehicle_type",
                ]
            ),
        ]

    def __str__(self):
        return self.user.email


class RiderLocation(TimeStampedModel):
    """
    Stores the rider's latest GPS location.

    This model represents the rider's current physical
    position and is used by the dispatch system for:

    • Nearby-rider matching
    • Distance calculation
    • Rider tracking
    • ETA calculation
    • Location freshness checks
    """

    rider = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="location",
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    speed = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text="Current rider speed in km/h.",
    )

    heading = models.PositiveSmallIntegerField(
        default=0,
        help_text="Direction of travel in degrees (0-359).",
    )

    accuracy = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
        help_text="GPS accuracy in meters.",
    )

    last_seen = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["last_seen"],
            ),
        ]

    def __str__(self):
        return (
            f"{self.rider.email} "
            f"({self.latitude}, {self.longitude})"
        )


class RiderStatistics(TimeStampedModel):
    rider = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rider_statistics",
    )

    acceptance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    cancellation_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    completed_deliveries = models.PositiveIntegerField(
        default=0,
    )

    def __str__(self):
        return f"Statistics - {self.rider.email}"