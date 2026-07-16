from django.db import models
from django.conf import settings
from common.models import TimeStampedModel
import uuid


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
        editable=False
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rider_profile"
    )
    vehicle_type = models.CharField(
        max_length=20,
        choices=VehicleType.choices
    )
    vehicle_plate_number = models.CharField(
        max_length=30
    )
    driver_license = models.ImageField(
        upload_to="licenses/"
    )
    nin = models.CharField(
        max_length=20
    )
    is_online = models.BooleanField(
        default=False
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
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
    def __str__(self):
        return self.user.email