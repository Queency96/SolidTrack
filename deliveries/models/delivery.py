from django.utils import timezone
import uuid
from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from decimal import Decimal
from riders.models import RiderProfile
import uuid



class Delivery(TimeStampedModel):

    # ==================================================
    # Delivery Type
    # ==================================================

    class DeliveryType(models.TextChoices):
        INSTANT = "INSTANT", "Instant"
        SCHEDULED = "SCHEDULED", "Scheduled"

    # ==================================================
    # Delivery Status
    # ==================================================

    class DeliveryStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"

        WAITING_FOR_RIDER = (
            "WAITING_FOR_RIDER",
            "Waiting for Rider",
        )

        RIDER_ASSIGNED = (
            "RIDER_ASSIGNED",
            "Rider Assigned",
        )

        RIDER_ACCEPTED = (
            "RIDER_ACCEPTED",
            "Rider Accepted",
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

        FAILED = (
            "FAILED",
            "Failed",
        )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ==================================================
    # Payment Status
    # ==================================================

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        REFUNDED = "REFUNDED", "Refunded"

    # ==================================================
    # Identity
    # ==================================================

    tracking_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
    )

    # ==================================================
    # Parties
    # ==================================================

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="deliveries",
    )

    vendor = models.ForeignKey(
        "vendors.VendorProfile",
        on_delete=models.PROTECT,
        related_name="deliveries",
        null=True,
        blank=True,
    )

    # ==================================================
    # Pickup Store
    # ==================================================
    #
    # For vendor deliveries, the selected VendorStore
    # is the official pickup location for the rider.
    #
    # The FK preserves the relationship with the store.
    #
    # The snapshot fields below preserve the exact
    # pickup information used when the delivery was created.
    #

    pickup_store = models.ForeignKey(
        "vendors.VendorStore",
        on_delete=models.PROTECT,
        related_name="deliveries",
        null=True,
        blank=True,
    )

    pickup_store_name = models.CharField(
        max_length=255,
        blank=True,
    )

    # ==================================================
    # Delivery Type / Status
    # ==================================================

    delivery_type = models.CharField(
        max_length=20,
        choices=DeliveryType.choices,
    )

    status = models.CharField(
        max_length=30,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )

    # ==================================================
    # Pickup Location Snapshot
    # ==================================================
    #
    # IMPORTANT:
    #
    # These are NOT dynamically read from VendorStore.
    #
    # They represent the exact location used for this
    # delivery at the time it was created.
    #
    # Dispatch, pricing and rider matching should use
    # these coordinates.
    #

    pickup_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    pickup_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    pickup_address = models.TextField()

    # ==================================================
    # Destination
    # ==================================================

    destination_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    destination_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    destination_address = models.TextField()

    # ==================================================
    # Delivery Requirements
    # ==================================================

    vehicle_type = models.CharField(
        max_length=20,
        choices=RiderProfile.VehicleType.choices,
        null=True,
        blank=True,
    )

    package_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )

    package_size = models.CharField(
        max_length=30,
        blank=True,
    )

    # ==================================================
    # Scheduling
    # ==================================================

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ==================================================
    # Pricing
    # ==================================================

    estimated_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    actual_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    distance_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    weight_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    surge_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    insurance_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    service_fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    # ==================================================
    # Notes
    # ==================================================

    notes = models.TextField(
        blank=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status"],
            ),
            models.Index(
                fields=["payment_status"],
            ),
            models.Index(
                fields=["vendor"],
            ),
            models.Index(
                fields=["customer"],
            ),
            models.Index(
                fields=["pickup_store"],
            ),
        ]

    # ==================================================
    # String
    # ==================================================

    def __str__(self):
        return self.tracking_number

    # ==================================================
    # Save
    # ==================================================

    def save(self, *args, **kwargs):

        if not self.tracking_number:
            self.tracking_number = (
                f"DLV-{uuid.uuid4().hex[:10].upper()}"
            )

        super().save(*args, **kwargs)

