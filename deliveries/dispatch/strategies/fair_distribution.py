from decimal import Decimal

from .base import BaseDispatchStrategy


class FairDistributionDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Fair-distribution dispatch strategy.

    Designed to distribute delivery opportunities fairly
    across eligible riders while still considering
    operational suitability.

    Scoring priorities
    ------------------
    1. Fair workload distribution
    2. Current active workload
    3. Recent assignment count
    4. Distance to pickup
    5. Rider reliability
    6. Acceptance rate
    7. Completion rate
    8. Rider rating
    9. Rider experience
    10. Cancellation penalty

    The strategy uses DispatchContext metadata for
    dispatch-attempt information that is not necessarily
    persisted directly on RiderProfile.

    Supported RiderMatch metadata:

        recent_assignment_count

    Supported DispatchContext metadata:

        average_active_jobs
        average_recent_assignments
        fairness_workload_weight
        fairness_recent_assignment_weight

    Defaults are provided when these values are absent.

    Higher scores indicate better rider matches.
    """

    # ==================================================
    # Score
    # ==================================================

    def score(
        self,
        context,
        match,
    ) -> Decimal:
        """
        Calculate the fair-distribution dispatch score.
        """

        self.validate_inputs(
            context,
            match,
        )

        config = context.config

        # ==================================================
        # Rider Metrics
        # ==================================================

        rating = self.decimal(
            match.rating,
        )

        acceptance_rate = (
            self._normalize_percentage(
                match.acceptance_rate,
            )
        )

        completion_rate = (
            self._normalize_percentage(
                match.completion_rate,
            )
        )

        cancellation_rate = (
            self._normalize_percentage(
                match.cancellation_rate,
            )
        )

        completed_deliveries = max(
            self.decimal(
                match.completed_deliveries,
            ),
            Decimal("0"),
        )

        active_jobs = max(
            self.decimal(
                match.active_jobs,
            ),
            Decimal("0"),
        )

        distance = max(
            self.decimal(
                match.distance_km,
            ),
            Decimal("0"),
        )

        # ==================================================
        # Recent Assignment Count
        # ==================================================

        recent_assignments = max(
            self.decimal(
                match.get_metadata(
                    "recent_assignment_count",
                    0,
                ),
            ),
            Decimal("0"),
        )

        # ==================================================
        # Configuration Weights
        # ==================================================

        rating_weight = self.decimal(
            config.rating_weight,
        )

        distance_weight = self.decimal(
            config.distance_weight,
        )

        workload_weight = self.decimal(
            config.workload_weight,
        )

        acceptance_weight = self.decimal(
            config.acceptance_rate_weight,
        )

        completion_weight = self.decimal(
            config.completion_rate_weight,
        )

        cancellation_weight = self.decimal(
            config.cancellation_weight,
        )

        experience_weight = self.decimal(
            config.experience_weight,
        )

        # ==================================================
        # Fairness Configuration
        # ==================================================

        fairness_workload_weight = (
            self._get_fairness_weight(
                context,
                "fairness_workload_weight",
                workload_weight,
            )
        )

        fairness_recent_weight = (
            self._get_fairness_weight(
                context,
                "fairness_recent_assignment_weight",
                workload_weight,
            )
        )

        # ==================================================
        # Workload Fairness
        # ==================================================
        #
        # Lower workload should produce a higher score.
        #
        # Example:
        #
        # active_jobs = 0
        #     factor = 1
        #
        # active_jobs = 1
        #     factor = 0.5
        #
        # active_jobs = 2
        #     factor = 0.33

        average_active_jobs = (
            self._get_context_decimal(
                context,
                "average_active_jobs",
                Decimal("0"),
            )
        )

        workload_factor = (
            self._calculate_fairness_factor(
                active_jobs,
                average_active_jobs,
            )
        )

        workload_fairness_score = (
            workload_factor
            * fairness_workload_weight
        )

        # ==================================================
        # Recent Assignment Fairness
        # ==================================================
        #
        # Riders who have recently received more jobs
        # should receive a lower score.

        average_recent_assignments = (
            self._get_context_decimal(
                context,
                "average_recent_assignments",
                Decimal("0"),
            )
        )

        recent_assignment_factor = (
            self._calculate_fairness_factor(
                recent_assignments,
                average_recent_assignments,
            )
        )

        recent_assignment_score = (
            recent_assignment_factor
            * fairness_recent_weight
        )

        # ==================================================
        # Distance
        # ==================================================

        distance_factor = (
            Decimal("1")
            / (
                Decimal("1")
                + distance
            )
        )

        distance_score = (
            distance_factor
            * distance_weight
        )

        # ==================================================
        # Rating
        # ==================================================

        rating_factor = min(
            max(
                rating / Decimal("5"),
                Decimal("0"),
            ),
            Decimal("1"),
        )

        rating_score = (
            rating_factor
            * rating_weight
        )

        # ==================================================
        # Acceptance Rate
        # ==================================================

        acceptance_score = (
            acceptance_rate
            * acceptance_weight
        )

        # ==================================================
        # Completion Rate
        # ==================================================

        completion_score = (
            completion_rate
            * completion_weight
        )

        # ==================================================
        # Cancellation Penalty
        # ==================================================

        cancellation_penalty = (
            cancellation_rate
            * cancellation_weight
        )

        # ==================================================
        # Experience
        # ==================================================

        experience_factor = (
            completed_deliveries
            / (
                completed_deliveries
                + Decimal("100")
            )
        )

        experience_score = (
            experience_factor
            * experience_weight
        )

        # ==================================================
        # Reliability
        # ==================================================

        reliability_factor = (
            acceptance_rate
            * completion_rate
            * (
                Decimal("1")
                - cancellation_rate
            )
        )

        reliability_score = (
            reliability_factor
            * (
                acceptance_weight
                + completion_weight
            )
            / Decimal("2")
        )

        # ==================================================
        # Final Score
        # ==================================================

        score = (
            workload_fairness_score
            + recent_assignment_score
            + distance_score
            + rating_score
            + acceptance_score
            + completion_score
            + experience_score
            + reliability_score
            - cancellation_penalty
        )

        # ==================================================
        # Scoring Metadata
        # ==================================================

        match.add_metadata(
            "scoring_strategy",
            "FAIR_DISTRIBUTION",
        )

        match.add_metadata(
            "active_jobs",
            active_jobs,
        )

        match.add_metadata(
            "recent_assignment_count",
            recent_assignments,
        )

        match.add_metadata(
            "average_active_jobs",
            average_active_jobs,
        )

        match.add_metadata(
            "average_recent_assignments",
            average_recent_assignments,
        )

        match.add_metadata(
            "workload_fairness_score",
            workload_fairness_score,
        )

        match.add_metadata(
            "recent_assignment_score",
            recent_assignment_score,
        )

        match.add_metadata(
            "distance_score",
            distance_score,
        )

        match.add_metadata(
            "rating_score",
            rating_score,
        )

        match.add_metadata(
            "acceptance_score",
            acceptance_score,
        )

        match.add_metadata(
            "completion_score",
            completion_score,
        )

        match.add_metadata(
            "experience_score",
            experience_score,
        )

        match.add_metadata(
            "reliability_score",
            reliability_score,
        )

        match.add_metadata(
            "cancellation_penalty",
            cancellation_penalty,
        )

        final_score = max(
            score,
            Decimal("0"),
        )

        match.add_metadata(
            "final_score",
            final_score,
        )

        return final_score

    # ==================================================
    # Fairness Factor
    # ==================================================

    @staticmethod
    def _calculate_fairness_factor(
        rider_value: Decimal,
        average_value: Decimal,
    ) -> Decimal:
        """
        Calculate a fairness factor.

        A rider below the current average receives a
        higher factor.

        A rider above the average receives a lower
        factor.

        The result is clamped between 0 and 1.
        """

        rider_value = max(
            rider_value,
            Decimal("0"),
        )

        average_value = max(
            average_value,
            Decimal("0"),
        )

        # ----------------------------------------------
        # No population average
        # ----------------------------------------------
        #
        # If there is no meaningful average yet,
        # treat the rider as neutral.

        if average_value <= 0:

            if rider_value <= 0:
                return Decimal("1")

            return Decimal("0.5")

        # ----------------------------------------------
        # Rider below average
        # ----------------------------------------------

        if rider_value < average_value:

            factor = (
                Decimal("1")
                - (
                    rider_value
                    / (
                        average_value
                        + Decimal("1")
                    )
                )
            )

            return min(
                max(
                    factor,
                    Decimal("0"),
                ),
                Decimal("1"),
            )

        # ----------------------------------------------
        # Rider equal to average
        # ----------------------------------------------

        if rider_value == average_value:
            return Decimal("0.5")

        # ----------------------------------------------
        # Rider above average
        # ----------------------------------------------

        excess = (
            rider_value
            - average_value
        )

        factor = (
            Decimal("0.5")
            / (
                Decimal("1")
                + excess
            )
        )

        return min(
            max(
                factor,
                Decimal("0"),
            ),
            Decimal("1"),
        )

    # ==================================================
    # Context Decimal
    # ==================================================

    @staticmethod
    def _get_context_decimal(
        context,
        key,
        default=Decimal("0"),
    ) -> Decimal:
        """
        Safely retrieve a Decimal value from
        DispatchContext metadata.
        """

        value = None

        # ----------------------------------------------
        # Context metadata
        # ----------------------------------------------

        metadata = getattr(
            context,
            "metadata",
            None,
        )

        if isinstance(metadata, dict):
            value = metadata.get(
                key,
            )

        # ----------------------------------------------
        # Context getter
        # ----------------------------------------------

        if value is None and hasattr(
            context,
            "get",
        ):
            value = context.get(
                key,
                None,
            )

        # ----------------------------------------------
        # Normalize
        # ----------------------------------------------

        if value is None:
            return default

        try:
            return Decimal(
                str(value)
            )
        except (
            TypeError,
            ValueError,
        ):
            return default

    # ==================================================
    # Fairness Weight
    # ==================================================

    @staticmethod
    def _get_fairness_weight(
        context,
        key,
        default,
    ) -> Decimal:
        """
        Resolve a fairness-specific scoring weight.

        DispatchContext metadata can override the normal
        workload weight without requiring new fields on
        DispatchConfiguration.

        Example:

            fairness_workload_weight=10
            fairness_recent_assignment_weight=8
        """

        value = FairDistributionDispatchStrategy._get_context_decimal(
            context,
            key,
            default,
        )

        return max(
            value,
            Decimal("0"),
        )

    # ==================================================
    # Percentage Normalization
    # ==================================================

    @staticmethod
    def _normalize_percentage(
        value,
    ) -> Decimal:
        """
        Normalize percentage/rate values.

        Supported:

            0
            0.75
            1
            75
            100

        Results:

            0
            0.75
            1
            0.75
            1
        """

        try:
            value = Decimal(
                str(value or 0)
            )
        except (
            TypeError,
            ValueError,
        ):
            return Decimal("0")

        if value <= 0:
            return Decimal("0")

        if value > 1:
            value /= Decimal("100")

        return min(
            value,
            Decimal("1"),
        )