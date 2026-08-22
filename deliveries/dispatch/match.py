from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from accounts.models import User


@dataclass(slots=True)
class RiderMatch:
    """
    Dispatch-layer representation of a rider.

    Contains:

    • Rider
    • Distance from pickup
    • Search radius
    • Active workload
    • Rider performance metrics
    • Rider score
    • Dispatch metadata

    RiderMatch provides normalized access to rider
    profile and rider statistics so dispatch strategies
    do not need to access Django models directly.
    """

    # ==================================================
    # Core
    # ==================================================

    rider: User

    distance: Decimal

    search_radius: Decimal

    active_delivery_count: int = 0

    # ==================================================
    # Scoring
    # ==================================================

    score: Decimal | None = None

    # ==================================================
    # Metadata
    # ==================================================

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    # ==================================================
    # Rider Profile
    # ==================================================

    @property
    def profile(self):
        """
        Return the rider's RiderProfile.
        """

        return getattr(
            self.rider,
            "rider_profile",
            None,
        )

    # ==================================================
    # Rider Location
    # ==================================================

    @property
    def location(self):
        """
        Return the rider's current location.
        """

        return getattr(
            self.rider,
            "location",
            None,
        )

    # ==================================================
    # Rider Statistics
    # ==================================================

    @property
    def statistics(self):
        """
        Return the rider's RiderStatistics.
        """

        return getattr(
            self.rider,
            "rider_statistics",
            None,
        )

    # ==================================================
    # Rating
    # ==================================================

    @property
    def rating(self) -> Decimal:
        """
        Return the rider's current rating.

        Rating is normalized to Decimal so all dispatch
        strategies operate consistently.
        """

        profile = self.profile

        if profile is None:
            return Decimal("0.00")

        return self._to_decimal(
            getattr(
                profile,
                "rating",
                0,
            )
        )

    # ==================================================
    # Acceptance Rate
    # ==================================================

    @property
    def acceptance_rate(self) -> Decimal:
        """
        Return the rider's acceptance rate.
        """

        statistics = self.statistics

        if statistics is None:
            return Decimal("0.00")

        return self._to_decimal(
            getattr(
                statistics,
                "acceptance_rate",
                0,
            )
        )

    # ==================================================
    # Completion Rate
    # ==================================================

    @property
    def completion_rate(self) -> Decimal:
        """
        Return the rider's completion rate.
        """

        statistics = self.statistics

        if statistics is None:
            return Decimal("0.00")

        return self._to_decimal(
            getattr(
                statistics,
                "completion_rate",
                0,
            )
        )

    # ==================================================
    # Cancellation Rate
    # ==================================================

    @property
    def cancellation_rate(self) -> Decimal:
        """
        Return the rider's cancellation rate.
        """

        statistics = self.statistics

        if statistics is None:
            return Decimal("0.00")

        return self._to_decimal(
            getattr(
                statistics,
                "cancellation_rate",
                0,
            )
        )

    # ==================================================
    # Completed Deliveries
    # ==================================================

    @property
    def completed_deliveries(self) -> int:
        """
        Return the rider's completed delivery count.
        """

        statistics = self.statistics

        if statistics is None:
            return 0

        return int(
            getattr(
                statistics,
                "completed_deliveries",
                0,
            )
            or 0
        )

    # ==================================================
    # Active Workload
    # ==================================================

    @property
    def active_jobs(self) -> int:
        """
        Return the rider's current active delivery count.

        This is an alias for active_delivery_count and
        provides a consistent interface for dispatch
        strategies.
        """

        return self.active_delivery_count

    # ==================================================
    # Distance
    # ==================================================

    @property
    def distance_km(self) -> Decimal:
        """
        Return distance from pickup in kilometers.
        """

        return self.distance

    # ==================================================
    # Search Radius
    # ==================================================

    @property
    def radius_km(self) -> Decimal:
        """
        Return the search radius used to locate
        this rider.
        """

        return self.search_radius

    # ==================================================
    # Rider ID
    # ==================================================

    @property
    def rider_id(self):
        """
        Return the rider's ID.
        """

        return self.rider.id

    # ==================================================
    # Score
    # ==================================================

    def set_score(
        self,
        score,
    ):
        """
        Set the calculated rider score.

        Decimal is used to keep dispatch scoring
        deterministic.
        """

        self.score = self._to_decimal(
            score,
        )

        return self

    # ==================================================
    # Score Status
    # ==================================================

    @property
    def is_scored(self) -> bool:
        """
        Determine whether this match has been scored.
        """

        return self.score is not None

    # ==================================================
    # Metadata
    # ==================================================

    def add_metadata(
        self,
        key: str,
        value: Any,
    ):
        """
        Add or update metadata associated with
        this rider match.
        """

        self.metadata[key] = value

        return self

    # ==================================================
    # Metadata Retrieval
    # ==================================================

    def get_metadata(
        self,
        key: str,
        default: Any = None,
    ):
        """
        Safely retrieve match metadata.
        """

        return self.metadata.get(
            key,
            default,
        )

    # ==================================================
    # Decimal Conversion
    # ==================================================

    @staticmethod
    def _to_decimal(
        value,
    ) -> Decimal:
        """
        Safely normalize numeric values to Decimal.

        Handles:
            • None
            • int
            • float
            • Decimal
            • numeric strings
        """

        if value is None:
            return Decimal("0")

        return Decimal(
            str(value)
        )