import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from common.models import TimeStampedModel

from .delivery import Delivery


class DeliveryAssignment(TimeStampedModel):
    """
    Represents the SINGLE lifetime assignment record for a Delivery.

    ================================================================
    CORE ARCHITECTURE
    ================================================================

    A Delivery can have EXACTLY ONE DeliveryAssignment row during
    its entire lifetime.

    First assignment:

        Delivery
            ↓
        DeliveryAssignment #1
            ↓
        Rider A

    If cancelled and explicitly restarted:

        DeliveryAssignment #1
            ↓
        CANCELLED + inactive
            ↓
        administrative restart
            ↓
        Delivery = WAITING_FOR_RIDER
            ↓
        same assignment row reused
            ↓
        Rider B

    NEVER:

        DeliveryAssignment #1
        DeliveryAssignment #2

    The OneToOneField is the database-level enforcement.

    ================================================================
    ASSIGNMENT REUSE
    ================================================================

    Reuse is permitted ONLY when:

        status == CANCELLED
        AND
        is_active == False

    AND:

        delivery.status == WAITING_FOR_RIDER

    The WAITING_FOR_RIDER state must have been reached through
    an explicit administrative/staff restart.

    ================================================================
    TERMINAL ASSIGNMENTS
    ================================================================

    COMPLETED
    REJECTED
    FAILED

    cannot be reused.

    CANCELLED is the only reusable assignment state.
    """

    # ============================================================
    # ASSIGNMENT STATUS
    # ============================================================

    class AssignmentStatus(models.TextChoices):

        PENDING = (
            "PENDING",
            "Pending",
        )

        ASSIGNED = (
            "ASSIGNED",
            "Assigned",
        )

        ACCEPTED = (
            "ACCEPTED",
            "Accepted",
        )

        EN_ROUTE_PICKUP = (
            "EN_ROUTE_PICKUP",
            "En Route to Pickup",
        )

        ARRIVED_PICKUP = (
            "ARRIVED_PICKUP",
            "Arrived at Pickup",
        )

        PICKED_UP = (
            "PICKED_UP",
            "Picked Up",
        )

        OUT_FOR_DELIVERY = (
            "OUT_FOR_DELIVERY",
            "Out for Delivery",
        )

        ARRIVED_DESTINATION = (
            "ARRIVED_DESTINATION",
            "Arrived at Destination",
        )

        COMPLETED = (
            "COMPLETED",
            "Completed",
        )

        REJECTED = (
            "REJECTED",
            "Rejected",
        )

        CANCELLED = (
            "CANCELLED",
            "Cancelled",
        )

        FAILED = (
            "FAILED",
            "Failed",
        )

    # ============================================================
    # PRIMARY KEY
    # ============================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ============================================================
    # DELIVERY
    # ============================================================

    delivery = models.OneToOneField(
        Delivery,
        on_delete=models.PROTECT,
        related_name="assignment",
        help_text=(
            "The single lifetime assignment for this delivery."
        ),
    )

    # ============================================================
    # RIDER
    # ============================================================

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="delivery_assignments",
    )

    # ============================================================
    # ASSIGNED BY
    # ============================================================

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_delivery_assignments",
        help_text=(
            "Admin/staff/system user that created the assignment. "
            "Null means system-generated."
        ),
    )

    # ============================================================
    # ACTIVE
    # ============================================================

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    # ============================================================
    # STATUS
    # ============================================================

    status = models.CharField(
        max_length=30,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.PENDING,
        db_index=True,
    )

    # ============================================================
    # LIFECYCLE TIMESTAMPS
    # ============================================================

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

    en_route_pickup_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    arrived_pickup_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    picked_up_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    out_for_delivery_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    arrived_destination_at = models.DateTimeField(
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

    failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ============================================================
    # REJECTION / CANCELLATION / FAILURE REASONS
    # ============================================================

    rejection_reason = models.TextField(
        blank=True,
        default="",
    )

    cancellation_reason = models.TextField(
        blank=True,
        default="",
    )

    failure_reason = models.TextField(
        blank=True,
        default="",
    )

    # ============================================================
    # NOTES
    # ============================================================

    notes = models.TextField(
        blank=True,
        default="",
    )

    # ============================================================
    # META
    # ============================================================

    class Meta:

        constraints = [
            models.UniqueConstraint(
                fields=["delivery"],
                name="unique_delivery_assignment",
            ),
        ]

        ordering = [
            "-assigned_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "delivery",
                    "status",
                ],
                name="assignment_delivery_status_idx",
            ),
            models.Index(
                fields=[
                    "rider",
                    "status",
                ],
                name="assignment_rider_status_idx",
            ),
            models.Index(
                fields=[
                    "rider",
                    "is_active",
                ],
                name="assignment_rider_active_idx",
            ),
            models.Index(
                fields=[
                    "status",
                ],
                name="assignment_status_idx",
            ),
            models.Index(
                fields=[
                    "is_active",
                ],
                name="assignment_active_idx",
            ),
            models.Index(
                fields=[
                    "assigned_at",
                ],
                name="assignment_assigned_at_idx",
            ),
        ]

    # ============================================================
    # STRING
    # ============================================================

    def __str__(self):

        rider_name = (
            self.rider.get_full_name()
            or getattr(
                self.rider,
                "email",
                None,
            )
            or str(self.rider_id)
        )

        tracking_number = getattr(
            self.delivery,
            "tracking_number",
            str(self.delivery_id),
        )

        return (
            f"{tracking_number} → {rider_name}"
        )

    # ============================================================
    # VALIDATION
    # ============================================================

    def clean(self):

        # ========================================================
        # DELIVERY
        # ========================================================

        if self.delivery_id is None:

            raise ValidationError(
                {
                    "delivery": (
                        "An assignment must belong "
                        "to a delivery."
                    )
                }
            )

        # ========================================================
        # RIDER
        # ========================================================

        if self.rider_id is None:

            raise ValidationError(
                {
                    "rider": (
                        "An assignment must have "
                        "a rider."
                    )
                }
            )

        # ========================================================
        # RIDER ROLE
        # ========================================================

        if hasattr(
            self.rider,
            "role",
        ):

            rider_role = str(
                self.rider.role
            ).upper()

            if rider_role != "RIDER":

                raise ValidationError(
                    {
                        "rider": (
                            "Only users with the RIDER "
                            "role can be assigned to "
                            "deliveries."
                        )
                    }
                )

        # ========================================================
        # TERMINAL ASSIGNMENT CANNOT BE ACTIVE
        # ========================================================

        terminal_statuses = {
            self.AssignmentStatus.COMPLETED,
            self.AssignmentStatus.REJECTED,
            self.AssignmentStatus.CANCELLED,
            self.AssignmentStatus.FAILED,
        }

        if (
            self.is_active
            and self.status in terminal_statuses
        ):

            raise ValidationError(
                {
                    "is_active": (
                        "A terminal assignment "
                        "cannot remain active."
                    )
                }
            )

        # ========================================================
        # COMPLETED
        # ========================================================

        if (
            self.status
            == self.AssignmentStatus.COMPLETED
            and self.completed_at is None
        ):

            raise ValidationError(
                {
                    "completed_at": (
                        "Completed timestamp is required "
                        "for a completed assignment."
                    )
                }
            )

        # ========================================================
        # REJECTED
        # ========================================================

        if (
            self.status
            == self.AssignmentStatus.REJECTED
            and self.rejected_at is None
        ):

            raise ValidationError(
                {
                    "rejected_at": (
                        "Rejected timestamp is required."
                    )
                }
            )

        # ========================================================
        # CANCELLED
        # ========================================================

        if (
            self.status
            == self.AssignmentStatus.CANCELLED
            and self.cancelled_at is None
        ):

            raise ValidationError(
                {
                    "cancelled_at": (
                        "Cancelled timestamp is required."
                    )
                }
            )

        # ========================================================
        # FAILED
        # ========================================================

        if (
            self.status
            == self.AssignmentStatus.FAILED
            and self.failed_at is None
        ):

            raise ValidationError(
                {
                    "failed_at": (
                        "Failed timestamp is required."
                    )
                }
            )

        # ========================================================
        # ACCEPTED / OPERATIONAL STATES
        # ========================================================

        accepted_states = {
            self.AssignmentStatus.ACCEPTED,
            self.AssignmentStatus.EN_ROUTE_PICKUP,
            self.AssignmentStatus.ARRIVED_PICKUP,
            self.AssignmentStatus.PICKED_UP,
            self.AssignmentStatus.OUT_FOR_DELIVERY,
            self.AssignmentStatus.ARRIVED_DESTINATION,
            self.AssignmentStatus.COMPLETED,
        }

        if (
            self.status in accepted_states
            and self.accepted_at is None
        ):

            raise ValidationError(
                {
                    "accepted_at": (
                        "Accepted timestamp is required "
                        "after the rider accepts the "
                        "assignment."
                    )
                }
            )

    # ============================================================
    # SAVE
    # ============================================================

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.full_clean()

        return super().save(
            *args,
            **kwargs,
        )

    # ============================================================
    # PROPERTIES
    # ============================================================

    @property
    def is_pending(self):

        return (
            self.status
            == self.AssignmentStatus.PENDING
        )

    # ------------------------------------------------------------

    @property
    def is_assigned(self):

        return (
            self.status
            == self.AssignmentStatus.ASSIGNED
        )

    # ------------------------------------------------------------

    @property
    def is_accepted(self):

        return self.status in {
            self.AssignmentStatus.ACCEPTED,
            self.AssignmentStatus.EN_ROUTE_PICKUP,
            self.AssignmentStatus.ARRIVED_PICKUP,
            self.AssignmentStatus.PICKED_UP,
            self.AssignmentStatus.OUT_FOR_DELIVERY,
            self.AssignmentStatus.ARRIVED_DESTINATION,
            self.AssignmentStatus.COMPLETED,
        }

    # ------------------------------------------------------------

    @property
    def is_picked_up(self):

        return self.status in {
            self.AssignmentStatus.PICKED_UP,
            self.AssignmentStatus.OUT_FOR_DELIVERY,
            self.AssignmentStatus.ARRIVED_DESTINATION,
            self.AssignmentStatus.COMPLETED,
        }

    # ------------------------------------------------------------

    @property
    def is_completed(self):

        return (
            self.status
            == self.AssignmentStatus.COMPLETED
        )

    # ------------------------------------------------------------

    @property
    def is_rejected(self):

        return (
            self.status
            == self.AssignmentStatus.REJECTED
        )

    # ------------------------------------------------------------

    @property
    def is_cancelled(self):

        return (
            self.status
            == self.AssignmentStatus.CANCELLED
        )

    # ------------------------------------------------------------

    @property
    def is_failed(self):

        return (
            self.status
            == self.AssignmentStatus.FAILED
        )

    # ------------------------------------------------------------

    @property
    def is_terminal(self):

        return self.status in {
            self.AssignmentStatus.COMPLETED,
            self.AssignmentStatus.REJECTED,
            self.AssignmentStatus.CANCELLED,
            self.AssignmentStatus.FAILED,
        }

    # ------------------------------------------------------------

    @property
    def can_be_reused(self):
        """
        Assignment-level reusable state.

        The service must additionally verify:

            delivery.status == WAITING_FOR_RIDER
        """

        return (
            self.status
            == self.AssignmentStatus.CANCELLED
            and not self.is_active
        )