from django.utils import timezone
import uuid
from django.conf import settings
from django.db import models
from common.models import TimeStampedModel
from decimal import Decimal
from riders.models import RiderProfile


class DispatchConfiguration(TimeStampedModel):
    """
    Global dispatch configuration.

    Only one active configuration should exist.
    """

    # ==================================================
    # Dispatch Strategy
    # ==================================================

    class DispatchStrategy(models.TextChoices):
        BALANCED = (
            "BALANCED",
            "Balanced",
        )

        NEAREST = (
            "NEAREST",
            "Nearest Rider",
        )

        PERFORMANCE = (
            "PERFORMANCE",
            "Performance Based",
        )

        VENDOR_PRIORITY = (
            "VENDOR_PRIORITY",
            "Vendor Priority",
        )

        CUSTOMER_PRIORITY = (
            "CUSTOMER_PRIORITY",
            "Customer Priority",
        )

        FAIR_DISTRIBUTION = (
            "FAIR_DISTRIBUTION",
            "Fair Distribution",
        )

        EXPRESS = (
            "EXPRESS",
            "Express Delivery",
        )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    # ==================================================
    # Identity
    # ==================================================

    name = models.CharField(
        max_length=100,
        unique=True,
    )

    dispatch_strategy = models.CharField(
        max_length=30,
        choices=DispatchStrategy.choices,
        default=DispatchStrategy.BALANCED,
        help_text=(
            "Determines how riders are ranked "
            "during dispatch."
        ),
    )

    # ==================================================
    # Search Radius
    # ==================================================

    initial_search_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=3,
    )

    maximum_search_radius_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15,
    )

    search_radius_increment_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=2,
    )

    # ==================================================
    # Rider Response
    # ==================================================

    rider_response_timeout_seconds = (
        models.PositiveIntegerField(
            default=30,
        )
    )

    max_rider_assignments = (
        models.PositiveSmallIntegerField(
            default=0,
            help_text=(
            "Maximum number of rider assignments "
            "allowed for a delivery. "
            "Use 0 for unlimited."
            ),
        )
    )

    auto_redispatch = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Matching Rules
    # ==================================================

    minimum_rider_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=3.50,
    )

    maximum_active_deliveries = (
        models.PositiveSmallIntegerField(
            default=2,
        )
    )

    # ==================================================
    # Dispatch Scoring Weights
    # ==================================================

    rating_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=10,
    )

    distance_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=2,
    )

    workload_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=5,
    )

    acceptance_rate_weight = (
        models.DecimalField(
            max_digits=6,
            decimal_places=2,
            default=4,
        )
    )

    completion_rate_weight = (
        models.DecimalField(
            max_digits=6,
            decimal_places=2,
            default=3,
        )
    )

    cancellation_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=8,
        help_text=(
            "Penalty applied to riders with "
            "higher cancellation rates."
        ),
    )

    experience_weight = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=2,
    )

    # ==================================================
    # Dispatch Behaviour
    # ==================================================

    offer_batch_size = (
        models.PositiveSmallIntegerField(
            default=1,
            help_text=(
                "Number of riders offered "
                "a delivery simultaneously."
            ),
        )
    )

    # ==================================================
    # Scheduling
    # ==================================================

    allow_scheduled_dispatch = (
        models.BooleanField(
            default=True,
        )
    )

    dispatch_before_pickup_minutes = (
        models.PositiveIntegerField(
            default=15,
        )
    )

    # ==================================================
    # Status
    # ==================================================

    is_active = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:
        ordering = (
            "-created_at",
        )

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):
        return self.name