from django.core.exceptions import ValidationError
from django.db import models


class StoreOperatingHour(models.Model):
    """
    Defines the operating schedule of a vendor store.

    Each store can have a different schedule for each
    day of the week.

    Example:

        Monday:
            08:00 - 18:00

        Tuesday:
            08:00 - 18:00

        Sunday:
            Closed

    The schedule can later be used by:

        • Product availability
        • Order processing
        • Rider pickup eligibility
        • Dispatch scheduling
        • Store management
    """

    # ==================================================
    # Store
    # ==================================================

    store = models.ForeignKey(
        "vendors.VendorStore",
        on_delete=models.CASCADE,
        related_name="operating_hours",
    )

    # ==================================================
    # Day
    # ==================================================

    class Weekday(models.IntegerChoices):
        MONDAY = (
            0,
            "Monday",
        )

        TUESDAY = (
            1,
            "Tuesday",
        )

        WEDNESDAY = (
            2,
            "Wednesday",
        )

        THURSDAY = (
            3,
            "Thursday",
        )

        FRIDAY = (
            4,
            "Friday",
        )

        SATURDAY = (
            5,
            "Saturday",
        )

        SUNDAY = (
            6,
            "Sunday",
        )

    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
    )

    # ==================================================
    # Operating Status
    # ==================================================

    is_closed = models.BooleanField(
        default=False,
    )

    # ==================================================
    # Opening / Closing Time
    # ==================================================

    opens_at = models.TimeField(
        null=True,
        blank=True,
    )

    closes_at = models.TimeField(
        null=True,
        blank=True,
    )

    # ==================================================
    # Rider Pickup
    # ==================================================
    #
    # A store may be open to customers but temporarily
    # unavailable for rider pickups.

    pickup_available = models.BooleanField(
        default=True,
    )

    # ==================================================
    # Metadata
    # ==================================================

    notes = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )

    # ==================================================
    # Timestamps
    # ==================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ==================================================
    # Meta
    # ==================================================

    class Meta:

        ordering = [
            "weekday",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "store",
                    "weekday",
                ],
                name=(
                    "unique_store_operating_hour_per_day"
                ),
            ),

        ]

        indexes = [

            models.Index(
                fields=[
                    "store",
                    "weekday",
                ],
            ),

            models.Index(
                fields=[
                    "store",
                    "pickup_available",
                ],
            ),

        ]

    # ==================================================
    # String Representation
    # ==================================================

    def __str__(self):

        if self.is_closed:

            return (
                f"{self.store.name} - "
                f"{self.get_weekday_display()} - "
                "Closed"
            )

        return (
            f"{self.store.name} - "
            f"{self.get_weekday_display()} - "
            f"{self.opens_at} - "
            f"{self.closes_at}"
        )

    # ==================================================
    # Validation
    # ==================================================

    def clean(self):
        """
        Validate operating-hour configuration.
        """

        # ----------------------------------------------
        # Closed day
        # ----------------------------------------------

        if self.is_closed:

            if (
                self.opens_at is not None
                or self.closes_at is not None
            ):
                raise ValidationError(
                    {
                        "opens_at": (
                            "Closed stores/days should "
                            "not have opening times."
                        ),
                        "closes_at": (
                            "Closed stores/days should "
                            "not have closing times."
                        ),
                    }
                )

            return

        # ----------------------------------------------
        # Open day
        # ----------------------------------------------

        if self.opens_at is None:

            raise ValidationError(
                {
                    "opens_at": (
                        "Opening time is required "
                        "when the store is open."
                    )
                }
            )

        if self.closes_at is None:

            raise ValidationError(
                {
                    "closes_at": (
                        "Closing time is required "
                        "when the store is open."
                    )
                }
            )

        # ----------------------------------------------
        # Same-day schedule
        # ----------------------------------------------

        if self.opens_at == self.closes_at:

            raise ValidationError(
                {
                    "closes_at": (
                        "Opening and closing times "
                        "cannot be identical."
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
    # Open Status
    # ==================================================

    @property
    def is_open(self):
        """
        Determine whether this schedule represents
        an operating day.
        """

        return not self.is_closed

    # ==================================================
    # Pickup Status
    # ==================================================

    @property
    def can_accept_pickup(self):
        """
        Determine whether rider pickup is permitted
        according to this schedule.
        """

        return (
            not self.is_closed
            and self.pickup_available
        )