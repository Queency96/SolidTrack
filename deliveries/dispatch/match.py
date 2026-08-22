from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from accounts.models import User


@dataclass(slots=True)
class RiderMatch:
    """
    Dispatch-layer representation of a rider.

    RiderMatch is the normalized boundary object between
    rider discovery and dispatch scoring.

    Contains:

        • Rider
        • Distance from pickup
        • Search radius
        • Active workload
        • Rider performance metrics
        • Rider score
        • Dispatch metadata

    RiderMatch intentionally does not perform database
    queries or dispatch decisions.

    RiderMatcher creates RiderMatch instances.

    RiderScorer calculates their score.

    DispatchPipeline ranks the matches.
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
    # Initialization
    # ==================================================

    def __post_init__(self):
        """
        Normalize values when the match is created.

        Dispatch calculations should operate on predictable
        numeric types.
        """

        if self.rider is None:
            raise ValueError(
                "RiderMatch requires a rider."
            )

        self.distance = self._normalize_non_negative(
            self.distance,
            field_name="distance",
        )

        self.search_radius = (
            self._normalize_non_negative(
                self.search_radius,
                field_name="search_radius",
            )
        )

        try:
            self.active_delivery_count = int(
                self.active_delivery_count or 0
            )
        except (TypeError, ValueError):
            raise ValueError(
                "active_delivery_count must be an integer."
            )

        if self.active_delivery_count < 0:
            raise ValueError(
                "active_delivery_count cannot be negative."
            )

        if self.score is not None:
            self.score = self._to_decimal(
                self.score,
            )

    # ==================================================
    # Rider Profile
    # ==================================================

    @property
    def profile(self):
        """
        Return the rider's RiderProfile.

        RiderProfile is expected to be exposed through
        the rider's reverse relation.
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

        This property provides normalized access for
        dispatch strategies without requiring them to
        understand the User model structure.
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

        Missing ratings are normalized to 0.00.
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

        Missing statistics are normalized to 0.00.
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

        Missing statistics are normalized to 0.00.
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

        Missing statistics are normalized to 0.00.
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

        value = getattr(
            statistics,
            "completed_deliveries",
            0,
        )

        try:
            value = int(value or 0)
        except (TypeError, ValueError):
            return 0

        return max(
            value,
            0,
        )

    # ==================================================
    # Active Workload
    # ==================================================

    @property
    def active_jobs(self) -> int:
        """
        Alias for active_delivery_count.

        This gives scoring strategies a consistent
        workload-oriented property.
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
        Return the search radius that produced
        this rider match.
        """

        return self.search_radius

    # ==================================================
    # Rider ID
    # ==================================================

    @property
    def rider_id(self):
        """
        Return the rider's primary key.
        """

        return getattr(
            self.rider,
            "id",
            None,
        )

    # ==================================================
    # Score
    # ==================================================

    def set_score(
        self,
        score,
    ):
        """
        Set the calculated rider score.

        Scores are normalized to Decimal so sorting and
        comparisons remain deterministic.
        """

        normalized_score = self._to_decimal(
            score,
        )

        if normalized_score < 0:
            raise ValueError(
                "Rider score cannot be negative."
            )

        self.score = normalized_score

        return self

    # ==================================================
    # Score Status
    # ==================================================

    @property
    def is_scored(self) -> bool:
        """
        Determine whether a rider score has been assigned.
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
        Add or replace match metadata.
        """

        if not key:
            raise ValueError(
                "Metadata key cannot be empty."
            )

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

        Supported values include:

            • None
            • int
            • float
            • Decimal
            • numeric strings

        Invalid numeric values are converted to zero.
        """

        if value is None:
            return Decimal("0")

        if isinstance(value, Decimal):
            return value

        try:
            return Decimal(
                str(value)
            )
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):
            return Decimal("0")

    # ==================================================
    # Non-Negative Decimal
    # ==================================================

    @classmethod
    def _normalize_non_negative(
        cls,
        value,
        *,
        field_name: str,
    ) -> Decimal:
        """
        Normalize a numeric value to Decimal and ensure
        that it is not negative.
        """

        value = cls._to_decimal(
            value,
        )

        if value < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return value