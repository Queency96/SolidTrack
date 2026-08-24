from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(slots=True)
class RiderMatch:
    """
    Represents a rider matched to a delivery.

    RiderMatch is created by RiderMatcher and enriched
    by RiderScorer and RiderRanker.

    Responsibilities
    ----------------
    • Store the matched rider
    • Store rider-to-pickup distance
    • Store the search radius used
    • Store active rider workload
    • Store scoring information
    • Store score breakdown
    • Store ranking metadata

    RiderMatch does NOT:
        • Find riders
        • Check rider eligibility
        • Calculate distance
        • Execute dispatch strategies
        • Rank riders
        • Create delivery offers
        • Assign riders
        • Notify riders
    """

    # ==================================================
    # Rider
    # ==================================================

    rider: Any

    # ==================================================
    # Matching Information
    # ==================================================

    distance_km: Decimal = Decimal("0")

    search_radius: Decimal = Decimal("0")

    active_delivery_count: int = 0

    # ==================================================
    # Scoring
    # ==================================================

    score: Decimal = Decimal("0")

    raw_score: Decimal | None = None

    scored: bool = False

    # ==================================================
    # Strategy Information
    # ==================================================

    strategy: str | None = None

    score_breakdown: dict[str, Any] = field(
        default_factory=dict,
    )

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
        Normalize match values after initialization.
        """

        # ----------------------------------------------
        # Distance
        # ----------------------------------------------

        self.distance_km = self._normalize_non_negative(
            self.distance_km,
        )

        # ----------------------------------------------
        # Search radius
        # ----------------------------------------------

        self.search_radius = (
            self._normalize_non_negative(
                self.search_radius,
            )
        )

        # ----------------------------------------------
        # Active workload
        # ----------------------------------------------

        try:
            self.active_delivery_count = int(
                self.active_delivery_count or 0,
            )
        except (
            TypeError,
            ValueError,
        ):
            self.active_delivery_count = 0

        if self.active_delivery_count < 0:
            self.active_delivery_count = 0

        # ----------------------------------------------
        # Score
        # ----------------------------------------------

        self.score = self._normalize_non_negative(
            self.score,
        )

        # ----------------------------------------------
        # Raw score
        # ----------------------------------------------

        if self.raw_score is not None:

            self.raw_score = self._normalize_score(
                self.raw_score,
            )

    # ==================================================
    # Scoring
    # ==================================================

    def set_score(
        self,
        score,
        strategy=None,
        breakdown=None,
        raw_score=None,
    ):
        """
        Store the calculated rider score.

        RiderScorer performs the actual scoring.

        RiderMatch only stores the result.

        Parameters
        ----------
        score:
            Final normalized dispatch score.

        strategy:
            Name of the dispatch strategy used.

        breakdown:
            Optional score component breakdown.

        raw_score:
            Optional score returned directly by the
            dispatch strategy.
        """

        self.score = self._normalize_score(
            score,
        )

        self.scored = True

        # ----------------------------------------------
        # Raw score
        # ----------------------------------------------

        if raw_score is not None:

            self.raw_score = (
                self._normalize_score(
                    raw_score,
                )
            )

        else:

            self.raw_score = self.score

        # ----------------------------------------------
        # Strategy
        # ----------------------------------------------

        if strategy is not None:

            self.strategy = str(
                strategy,
            )

        # ----------------------------------------------
        # Breakdown
        # ----------------------------------------------

        if breakdown is not None:

            self.score_breakdown = dict(
                breakdown,
            )

        return self

    def reset_score(
        self,
    ):
        """
        Reset all scoring information.

        Useful when a match is re-scored during
        redispatch or when dispatch configuration
        changes.
        """

        self.score = Decimal("0")

        self.raw_score = None

        self.scored = False

        self.strategy = None

        self.score_breakdown.clear()

        return self

    # ==================================================
    # Score Breakdown
    # ==================================================

    def add_score_component(
        self,
        name,
        value,
    ):
        """
        Add an individual scoring component.

        Example
        -------
        match.add_score_component(
            "distance",
            Decimal("85"),
        )
        """

        if not name:
            raise ValueError(
                "Score component name is required."
            )

        self.score_breakdown[
            str(name)
        ] = self._normalize_score(
            value,
        )

        return self

    def get_score_component(
        self,
        name,
        default=None,
    ):
        """
        Retrieve a scoring component.
        """

        return self.score_breakdown.get(
            name,
            default,
        )

    # ==================================================
    # Metadata
    # ==================================================

    def add_metadata(
        self,
        key,
        value,
    ):
        """
        Store arbitrary rider-match metadata.
        """

        if not key:
            raise ValueError(
                "Metadata key is required."
            )

        self.metadata[
            str(key)
        ] = value

        return self

    def get_metadata(
        self,
        key,
        default=None,
    ):
        """
        Retrieve rider-match metadata.
        """

        return self.metadata.get(
            key,
            default,
        )

    def get(
        self,
        key,
        default=None,
    ):
        """
        Dictionary-style metadata access.
        """

        return self.get_metadata(
            key,
            default,
        )

    # ==================================================
    # Workload
    # ==================================================

    @property
    def has_active_deliveries(
        self,
    ):
        """
        Return True when the rider has active deliveries.
        """

        return (
            self.active_delivery_count > 0
        )

    @property
    def is_idle(
        self,
    ):
        """
        Return True when the rider has no active
        deliveries.
        """

        return (
            self.active_delivery_count == 0
        )

    # ==================================================
    # Distance
    # ==================================================

    @property
    def distance(
        self,
    ):
        """
        Backward-compatible alias for distance_km.
        """

        return self.distance_km

    @distance.setter
    def distance(
        self,
        value,
    ):
        self.distance_km = (
            self._normalize_non_negative(
                value,
            )
        )

    @property
    def distance_meters(
        self,
    ):
        """
        Return rider-to-pickup distance in meters.
        """

        return (
            self.distance_km
            * Decimal("1000")
        )

    @property
    def within_search_radius(
        self,
    ):
        """
        Determine whether the rider is inside the
        search radius used to create this match.
        """

        return (
            self.distance_km
            <= self.search_radius
        )

    # ==================================================
    # Scoring State
    # ==================================================

    @property
    def is_scored(
        self,
    ):
        """
        Alias used by DispatchPipeline and RiderRanker.
        """

        return self.scored

    @property
    def has_score(
        self,
    ):
        """
        Return True when the rider has been scored.
        """

        return self.scored

    @property
    def has_raw_score(
        self,
    ):
        """
        Return True when a raw strategy score exists.
        """

        return (
            self.raw_score is not None
        )

    @property
    def has_score_breakdown(
        self,
    ):
        """
        Return True when scoring components exist.
        """

        return bool(
            self.score_breakdown,
        )

    # ==================================================
    # Rider Identity
    # ==================================================

    @property
    def rider_id(
        self,
    ):
        """
        Return the rider primary key.
        """

        if self.rider is None:
            return None

        return getattr(
            self.rider,
            "id",
            None,
        )

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ):
        """
        Convert the match into a JSON-friendly
        dictionary.
        """

        return {
            "rider_id": self.rider_id,

            "distance_km": str(
                self.distance_km,
            ),

            "distance_meters": str(
                self.distance_meters,
            ),

            "search_radius": str(
                self.search_radius,
            ),

            "active_delivery_count": (
                self.active_delivery_count
            ),

            "score": str(
                self.score,
            ),

            "raw_score": (
                str(self.raw_score)
                if self.raw_score is not None
                else None
            ),

            "scored": self.scored,

            "strategy": self.strategy,

            "score_breakdown": (
                self._serialize_value(
                    self.score_breakdown,
                )
            ),

            "metadata": (
                self._serialize_value(
                    self.metadata,
                )
            ),
        }

    # ==================================================
    # Decimal Helpers
    # ==================================================

    @staticmethod
    def _to_decimal(
        value,
        default=Decimal("0"),
    ) -> Decimal:
        """
        Safely convert a value to Decimal.
        """

        if value is None:
            return default

        try:

            return Decimal(
                str(value),
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):

            return default

    @classmethod
    def _normalize_score(
        cls,
        value,
    ) -> Decimal:
        """
        Normalize a score to a finite,
        non-negative Decimal.
        """

        if value is None:
            raise ValueError(
                "Score cannot be None."
            )

        try:

            value = Decimal(
                str(value),
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                f"Invalid score: {value!r}."
            ) from exc

        if not value.is_finite():
            raise ValueError(
                f"Score must be finite: {value!r}."
            )

        return max(
            value,
            Decimal("0"),
        )

    @classmethod
    def _normalize_non_negative(
        cls,
        value,
    ) -> Decimal:
        """
        Normalize a numeric value to a finite,
        non-negative Decimal.
        """

        try:

            value = Decimal(
                str(value),
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):

            value = Decimal("0")

        if not value.is_finite():
            return Decimal("0")

        return max(
            value,
            Decimal("0"),
        )

    # ==================================================
    # Serialization Helper
    # ==================================================

    @classmethod
    def _serialize_value(
        cls,
        value,
    ):
        """
        Recursively convert Decimal values and
        containers into JSON-friendly values.
        """

        if isinstance(
            value,
            Decimal,
        ):
            return str(value)

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): cls._serialize_value(
                    item,
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                cls._serialize_value(
                    item,
                )
                for item in value
            ]

        if isinstance(
            value,
            set,
        ):
            return [
                cls._serialize_value(
                    item,
                )
                for item in value
            ]

        return value

    # ==================================================
    # Representation
    # ==================================================

    def __repr__(
        self,
    ):
        """
        Developer-friendly representation.
        """

        return (
            "RiderMatch("
            f"rider_id={self.rider_id!r}, "
            f"distance_km={self.distance_km!r}, "
            f"score={self.score!r}, "
            f"scored={self.scored!r}, "
            f"strategy={self.strategy!r}"
            ")"
        )