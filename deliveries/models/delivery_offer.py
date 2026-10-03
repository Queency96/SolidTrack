import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from common.models import TimeStampedModel


class DeliveryOffer(TimeStampedModel):
    """
    Represents a single dispatch offer made to a rider for a
    delivery.

    ================================================================
    ARCHITECTURE
    ================================================================

    Offers are NOT assignments.

    - A Delivery may have MANY DeliveryOffer rows over its
      lifetime (one per rider attempted, per attempt).
    - A Delivery may have AT MOST ONE DeliveryAssignment row.
    - An offer does NOT consume the assignment slot.
    - Offer lifecycle is owned exclusively by DeliveryOfferService.

    Persistent offer history is the source of truth for:

        - previously offered rider exclusions
        - dispatch attempt number
        - redispatch decisions

    ================================================================
    DUPLICATE PENDING OFFER RULE
    ================================================================

    The database enforces that a given (delivery, rider) pair
    cannot have two simultaneous PENDING offers.

    The same rider MAY receive a new offer for the same delivery
    after a previous offer has been resolved
    (ACCEPTED / REJECTED / EXPIRED / CANCELLED).
    """

    class Status(models.TextChoices):

        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    # ==================================================
    # PRIMARY KEY
    # ==================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ==================================================
    # RELATIONSHIPS
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
    # OFFER STATE
    # ==================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    # ==================================================
    # DISPATCH INFORMATION
    # ==================================================

    search_radius = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )

    # ==================================================
    # TIMESTAMPS
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
    # RESPONSE
    # ==================================================

    rejection_reason = models.TextField(
        blank=True,
        default="",
    )

    # ==================================================
    # META
    # ==================================================

    class Meta:

        ordering = ("-offered_at",)

        constraints = [
            models.UniqueConstraint(
                fields=["delivery", "rider"],
                condition=Q(status="PENDING"),
                name="unique_pending_offer_per_delivery_rider",
            ),
        ]

        indexes = [
            models.Index(
                fields=["delivery", "status"],
                name="offer_delivery_status_idx",
            ),
            models.Index(
                fields=["rider", "status"],
                name="offer_rider_status_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="offer_expires_at_idx",
            ),
        ]

    # ==================================================
    # STRING
    # ==================================================

    def __str__(self):

        rider_name = (
            self.rider.get_full_name()
            or getattr(self.rider, "email", None)
            or str(self.rider_id)
        )

        tracking_number = getattr(
            self.delivery,
            "tracking_number",
            str(self.delivery_id),
        )

        return f"{tracking_number} → {rider_name}"

    # ==================================================
    # VALIDATION
    # ==================================================

    def clean(self):

        # --------------------------------------------------
        # DELIVERY
        # --------------------------------------------------

        if self.delivery_id is None:
            raise ValidationError(
                {"delivery": "An offer must belong to a delivery."}
            )

        # --------------------------------------------------
        # RIDER
        # --------------------------------------------------

        if self.rider_id is None:
            raise ValidationError(
                {"rider": "An offer must have a rider."}
            )

        # --------------------------------------------------
        # EXPIRY MUST BE AFTER OFFER TIME
        # --------------------------------------------------
        #
        # offered_at uses auto_now_add=True, so on first save it is
        # not yet populated when clean() runs. Guard on presence.
        # --------------------------------------------------

        if (
            self.expires_at is not None
            and self.offered_at is not None
            and self.expires_at <= self.offered_at
        ):
            raise ValidationError(
                {
                    "expires_at": (
                        "Offer expiry must be after the offer time."
                    )
                }
            )

    # ==================================================
    # SAVE
    # ==================================================

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    # ==================================================
    # PROPERTIES
    # ==================================================

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    # --------------------------------------------------

    @property
    def is_accepted(self):
        return self.status == self.Status.ACCEPTED

    # --------------------------------------------------

    @property
    def is_rejected(self):
        return self.status == self.Status.REJECTED

    # --------------------------------------------------

    @property
    def is_expired(self):
        return self.status == self.Status.EXPIRED

    # --------------------------------------------------

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    # --------------------------------------------------

    @property
    def is_terminal(self):
        """
        True for any resolved offer state.

        PENDING is the only non-terminal state.
        """
        return self.status in {
            self.Status.ACCEPTED,
            self.Status.REJECTED,
            self.Status.EXPIRED,
            self.Status.CANCELLED,
        }