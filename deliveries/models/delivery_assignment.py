import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from common.models import TimeStampedModel
from .delivery import Delivery


class DeliveryAssignment(TimeStampedModel):
    """
    Represents the assignment of a rider to a Delivery.

    Architecture:

        Order
          ↓
        OrderFulfillment
          ↓
        Delivery
          ↓
        DeliveryOffer
          ↓
        DeliveryAssignment
          ↓
        Rider

    A Delivery may have multiple historical assignments,
    but only one active assignment at a time.

    DeliveryAssignment is responsible for the rider's
    operational lifecycle after assignment.
    """

    # ==================================================
    # Assignment Status
    # ==================================================

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

    # ==================================================
    # ID
    # ==================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # Delivery
    # ==================================================

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    # ==================================================
    # Rider
    # ==================================================

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="delivery_assignments",
    )

    # ==================================================
    # Assignment Source
    # ==================================================

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_delivery_assignments",
        help_text=(
            "Admin or system user that created "
            "the assignment. Null means system-generated."
        ),
    )

    # ==================================================
    # Active Assignment
    # ==================================================

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    # ==================================================
    # Status
    # ==================================================

    status = models.CharField(
        max_length=30,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.PENDING,
        db_index=True,
    )

    # ==================================================
    # Lifecycle Timestamps
    # ==================================================

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

    rejected_at = models.DateTimeField(
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

    # ==================================================
    # Rejection / Cancellation / Failure
    # ==================================================

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

    # ==================================================
    # Notes
    # ==================================================

    notes = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "-assigned_at",
        ]

        constraints = [

            # ------------------------------------------
            # Only one active assignment per delivery
            # ------------------------------------------

            models.UniqueConstraint(
                fields=[
                    "delivery",
                ],
                condition=Q(
                    is_active=True,
                ),
                name="unique_active_delivery_assignment",
            ),

        ]

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
                    "rider",
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "status",
                ],
            ),

            models.Index(
                fields=[
                    "is_active",
                ],
            ),

            models.Index(
                fields=[
                    "assigned_at",
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
            f"{self.delivery.tracking_number} "
            f"→ {rider_name}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):

        # ----------------------------------------------
        # Delivery
        # ----------------------------------------------

        if self.delivery_id is None:

            raise ValidationError(
                {
                    "delivery": (
                        "An assignment must "
                        "belong to a delivery."
                    )
                }
            )

        # ----------------------------------------------
        # Rider
        # ----------------------------------------------

        if self.rider_id is None:

            raise ValidationError(
                {
                    "rider": (
                        "An assignment must "
                        "have a rider."
                    )
                }
            )

        # ----------------------------------------------
        # Rider Role
        # ----------------------------------------------

        if hasattr(self.rider, "role"):

            rider_role = str(
                self.rider.role
            ).upper()

            if rider_role != "RIDER":

                raise ValidationError(
                    {
                        "rider": (
                            "Only users with the "
                            "RIDER role can be "
                            "assigned to deliveries."
                        )
                    }
                )

        # ----------------------------------------------
        # Active Assignment
        # ----------------------------------------------

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

        # ----------------------------------------------
        # Completed
        # ----------------------------------------------

        if (
            self.status
            == self.AssignmentStatus.COMPLETED
            and self.completed_at is None
        ):

            raise ValidationError(
                {
                    "completed_at": (
                        "Completed timestamp is "
                        "required for a completed "
                        "assignment."
                    )
                }
            )

        # ----------------------------------------------
        # Rejected
        # ----------------------------------------------

        if (
            self.status
            == self.AssignmentStatus.REJECTED
            and self.rejected_at is None
        ):

            raise ValidationError(
                {
                    "rejected_at": (
                        "Rejected timestamp is "
                        "required."
                    )
                }
            )

        # ----------------------------------------------
        # Cancelled
        # ----------------------------------------------

        if (
            self.status
            == self.AssignmentStatus.CANCELLED
            and self.cancelled_at is None
        ):

            raise ValidationError(
                {
                    "cancelled_at": (
                        "Cancelled timestamp is "
                        "required."
                    )
                }
            )

        # ----------------------------------------------
        # Failed
        # ----------------------------------------------

        if (
            self.status
            == self.AssignmentStatus.FAILED
            and self.failed_at is None
        ):

            raise ValidationError(
                {
                    "failed_at": (
                        "Failed timestamp is "
                        "required."
                    )
                }
            )

        # ----------------------------------------------
        # Accepted
        # ----------------------------------------------

        if (
            self.status
            in {
                self.AssignmentStatus.ACCEPTED,
                self.AssignmentStatus.EN_ROUTE_PICKUP,
                self.AssignmentStatus.ARRIVED_PICKUP,
                self.AssignmentStatus.PICKED_UP,
                self.AssignmentStatus.OUT_FOR_DELIVERY,
                self.AssignmentStatus.ARRIVED_DESTINATION,
                self.AssignmentStatus.COMPLETED,
            }
            and self.accepted_at is None
        ):

            raise ValidationError(
                {
                    "accepted_at": (
                        "Accepted timestamp is "
                        "required after the rider "
                        "accepts the assignment."
                    )
                }
            )

    # ==================================================
    # Save
    # ==================================================

    def save(
        self,
        *args,
        **kwargs,
    ):

        self.full_clean()

        super().save(
            *args,
            **kwargs,
        )

    # ==================================================
    # Properties
    # ==================================================

    @property
    def is_pending(self):

        return (
            self.status
            == self.AssignmentStatus.PENDING
        )

    @property
    def is_accepted(self):

        return (
            self.status
            in {
                self.AssignmentStatus.ACCEPTED,
                self.AssignmentStatus.EN_ROUTE_PICKUP,
                self.AssignmentStatus.ARRIVED_PICKUP,
                self.AssignmentStatus.PICKED_UP,
                self.AssignmentStatus.OUT_FOR_DELIVERY,
                self.AssignmentStatus.ARRIVED_DESTINATION,
                self.AssignmentStatus.COMPLETED,
            }
        )

    @property
    def is_picked_up(self):

        return (
            self.status
            in {
                self.AssignmentStatus.PICKED_UP,
                self.AssignmentStatus.OUT_FOR_DELIVERY,
                self.AssignmentStatus.ARRIVED_DESTINATION,
                self.AssignmentStatus.COMPLETED,
            }
        )

    @property
    def is_completed(self):

        return (
            self.status
            == self.AssignmentStatus.COMPLETED
        )

    @property
    def is_rejected(self):

        return (
            self.status
            == self.AssignmentStatus.REJECTED
        )

    @property
    def is_cancelled(self):

        return (
            self.status
            == self.AssignmentStatus.CANCELLED
        )

    @property
    def is_failed(self):

        return (
            self.status
            == self.AssignmentStatus.FAILED
        )

    @property
    def is_terminal(self):

        return self.status in {
            self.AssignmentStatus.COMPLETED,
            self.AssignmentStatus.REJECTED,
            self.AssignmentStatus.CANCELLED,
            self.AssignmentStatus.FAILED,
        }