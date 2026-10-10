import uuid
from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from decimal import Decimal
from django.core.exceptions import ValidationError



class RiderProfile(TimeStampedModel):

    class VehicleType(models.TextChoices):
        BIKE = "BIKE", "Bike"
        CAR = "CAR", "Car"
        VAN = "VAN", "Van"
        TRUCK = "TRUCK", "Truck"

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





"""
Rider earning ledger.

One row per completed DeliveryAssignment. The row is created
the moment the assignment completes, and settled later by a
Celery task that credits the rider's wallet.
"""
class RiderEarning(TimeStampedModel):
    """
    Ledger entry representing the amount owed to a rider for
    a completed delivery.

    Lifecycle
    ---------
    PENDING   — created when the assignment completes
    SETTLED   — wallet credited, wallet_transaction populated
    FAILED    — settlement attempted but errored; retryable

    Idempotency
    -----------
    The `assignment` field is a OneToOneField, so at most one
    earning row can exist per assignment. This is the same
    pattern as DeliveryAssignment.delivery.
    """

    class Status(models.TextChoices):
        PENDING = ("PENDING", "Pending")
        SETTLED = ("SETTLED", "Settled")
        FAILED = ("FAILED", "Failed")

    # ==================================================
    # ID
    # ==================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Rider
    # ==================================================

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rider_earnings",
        db_index=True,
    )

    # ==================================================
    # Assignment
    # ==================================================
    #
    # OneToOne enforces one earning row per assignment.
    # ==================================================

    assignment = models.OneToOneField(
        "deliveries.DeliveryAssignment",
        on_delete=models.PROTECT,
        related_name="rider_earning",
    )

    # ==================================================
    # Amounts
    # ==================================================

    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=(
            "The delivery fee charged to the customer. "
            "Recorded at the moment of completion."
        ),
    )

    commission_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=(
            "Platform commission deducted from the gross. "
            "Snapshotted at the moment of completion from "
            "the active PlatformCommission, so later config "
            "changes do not affect historical earnings."
        ),
    )

    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=(
            "Amount credited to the rider. Computed as "
            "gross_amount - commission_amount."
        ),
    )

    currency = models.CharField(
        max_length=3,
        default="NGN",
    )

    # ==================================================
    # Status
    # ==================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # ==================================================
    # Settlement
    # ==================================================

    wallet_transaction = models.OneToOneField(
        "wallet.WalletTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rider_earning",
        help_text="The wallet credit created when this earning settled.",
    )

    settled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["rider", "status"]),
        ]

        verbose_name = "Rider Earning"
        verbose_name_plural = "Rider Earnings"

    # ==================================================
    # String
    # ==================================================

    def __str__(self):

        return (
            f"Earning {self.net_amount} "
            f"for assignment {self.assignment_id}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        if self.rider_id is None:
            raise ValidationError(
                {"rider": "A rider is required."}
            )

        if self.assignment_id is None:
            raise ValidationError(
                {"assignment": "An assignment is required."}
            )

        if self.gross_amount < Decimal("0.00"):
            raise ValidationError(
                {"gross_amount": "Gross amount cannot be negative."}
            )

        if self.commission_amount < Decimal("0.00"):
            raise ValidationError(
                {
                    "commission_amount": (
                        "Commission cannot be negative."
                    )
                }
            )

        if self.commission_amount > self.gross_amount:
            raise ValidationError(
                {
                    "commission_amount": (
                        "Commission cannot exceed gross amount."
                    )
                }
            )

        expected_net = self.gross_amount - self.commission_amount

        if self.net_amount != expected_net:
            raise ValidationError(
                {
                    "net_amount": (
                        f"Net amount must equal "
                        f"gross - commission ({expected_net})."
                    )
                }
            )

        if (
            self.status == self.Status.SETTLED
            and self.settled_at is None
        ):
            raise ValidationError(
                {
                    "settled_at": (
                        "A settled earning requires a "
                        "settled timestamp."
                    )
                }
            )

        if (
            self.status == self.Status.SETTLED
            and self.wallet_transaction_id is None
        ):
            raise ValidationError(
                {
                    "wallet_transaction": (
                        "A settled earning must reference "
                        "the wallet transaction."
                    )
                }
            )

        if (
            self.status == self.Status.FAILED
            and not self.failure_reason
        ):
            raise ValidationError(
                {
                    "failure_reason": (
                        "A failed earning requires a reason."
                    )
                }
            )

    # ==================================================
    # Save
    # ==================================================

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ==================================================
    # Properties
    # ==================================================

    @property
    def is_settled(self):
        return self.status == self.Status.SETTLED

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_failed(self):
        return self.status == self.Status.FAILED





"""
Platform commission configuration.

Defines the percentage the platform retains from each
delivery fee. Only one row is active at a time; new
settlements read the active row.

Historical earnings snapshot their commission, so
changing the active rate does not retroactively affect
already-created RiderEarning rows.
"""
class PlatformCommission(TimeStampedModel):
    """
    Commission rate applied to a rider's delivery fee.

    Percentage is expressed in the range 0.00 - 100.00.

    Only one row should be marked is_active=True at a time.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=(
            "Human-readable label, e.g. 'Default 10%'."
        ),
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=(
            "Commission percentage applied to the gross "
            "delivery fee. Range: 0.00 to 100.00."
        ),
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    notes = models.TextField(
        blank=True,
        default="",
    )

    class Meta:

        ordering = ["-is_active", "-created_at"]

        verbose_name = "Platform Commission"
        verbose_name_plural = "Platform Commissions"

    def __str__(self):

        return (
            f"{self.name} "
            f"({self.percentage}%)"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        if self.percentage < Decimal("0.00"):
            raise ValidationError(
                {"percentage": "Percentage cannot be negative."}
            )

        if self.percentage > Decimal("100.00"):
            raise ValidationError(
                {
                    "percentage": (
                        "Percentage cannot exceed 100."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # ==================================================
    # Class helpers
    # ==================================================

    @classmethod
    def get_active(cls):
        """
        Return the currently active commission config,
        or None if none is configured.

        None means zero commission.
        """

        return (
            cls.objects
            .filter(is_active=True)
            .order_by("-created_at")
            .first()
        )

    @classmethod
    def compute_commission(cls, gross_amount):
        """
        Return (commission, net) for a given gross amount
        using the active commission config.

        If no active config exists, commission is zero.
        """

        commission_config = cls.get_active()

        if commission_config is None:
            return Decimal("0.00"), gross_amount

        percentage = commission_config.percentage

        commission = (
            gross_amount * percentage / Decimal("100.00")
        ).quantize(Decimal("0.01"))

        net = gross_amount - commission

        if net < Decimal("0.00"):
            net = Decimal("0.00")

        return commission, net