from decimal import Decimal

from .base import BaseDispatchStrategy


class FairDistributionDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Fair-distribution dispatch strategy.

    This strategy attempts to distribute delivery
    opportunities fairly among eligible riders.

    Priority
    --------
    1. Riders with fewer completed deliveries receive
       a stronger opportunity bonus.
    2. Riders with fewer recent/active jobs are preferred.
    3. Riders with good acceptance and completion rates
       remain favored.
    4. Distance is still considered so fairness does
       not result in unreasonable rider selection.
    5. High cancellation rates are penalized.
    6. Rider rating remains a quality safeguard.

    The strategy uses the configured DispatchConfiguration
    weights wherever possible.

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
        Calculate a fair-distribution score.

        The key difference from other strategies is that
        rider experience is treated as a balancing factor:

            fewer completed deliveries
                →
            higher opportunity score

        This prevents highly experienced riders from
        receiving the majority of dispatch opportunities.
        """

        self.validate_inputs(
            context,
            match,
        )

        config = context.config

        # ----------------------------------------------
        # Rider metrics
        # ----------------------------------------------

        rating = self.decimal(
            match.rating,
        )

        acceptance_rate = self._normalize_percentage(
            match.acceptance_rate,
        )

        completion_rate = self._normalize_percentage(
            match.completion_rate,
        )

        cancellation_rate = self._normalize_percentage(
            match.cancellation_rate,
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

        # ----------------------------------------------
        # Configuration weights
        # ----------------------------------------------

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

        # ----------------------------------------------
        # Rating
        # ----------------------------------------------

        rating_factor = min(
            rating / Decimal("5"),
            Decimal("1"),
        )

        rating_score = (
            rating_factor
            * rating_weight
        )

        # ----------------------------------------------
        # Acceptance
        # ----------------------------------------------

        acceptance_score = (
            acceptance_rate
            * acceptance_weight
        )

        # ----------------------------------------------
        # Completion
        # ----------------------------------------------

        completion_score = (
            completion_rate
            * completion_weight
        )

        # ----------------------------------------------
        # Cancellation penalty
        # ----------------------------------------------

        cancellation_penalty = (
            cancellation_rate
            * cancellation_weight
        )

        # ----------------------------------------------
        # Distance
        # ----------------------------------------------
        #
        # Closer riders still receive an advantage.
        #
        # 0 km → 1.0
        # 1 km → 0.5
        # 2 km → 0.333...
        #
        # This prevents distance from completely
        # dominating fairness.

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

        # ----------------------------------------------
        # Workload fairness
        # ----------------------------------------------
        #
        # Riders carrying fewer active deliveries
        # receive a higher score.

        workload_factor = (
            Decimal("1")
            / (
                Decimal("1")
                + active_jobs
            )
        )

        workload_score = (
            workload_factor
            * workload_weight
        )

        # ----------------------------------------------
        # Fair opportunity score
        # ----------------------------------------------
        #
        # Riders with fewer completed deliveries receive
        # a larger opportunity bonus.
        #
        # Diminishing returns prevent a rider with zero
        # deliveries from receiving an overwhelmingly
        # large advantage.

        opportunity_factor = (
            Decimal("1")
            / (
                Decimal("1")
                + completed_deliveries
            )
        )

        opportunity_score = (
            opportunity_factor
            * experience_weight
        )

        # ----------------------------------------------
        # Fairness bonus
        # ----------------------------------------------
        #
        # Give additional importance to riders who have
        # relatively low experience while still requiring
        # acceptable service quality.
        #
        # Poor completion/cancellation performance should
        # not be rewarded merely because the rider has
        # received fewer deliveries.

        reliability_factor = (
            completion_rate
            * (
                Decimal("1")
                - cancellation_rate
            )
        )

        fairness_bonus = (
            opportunity_factor
            * reliability_factor
            * experience_weight
        )

        # ----------------------------------------------
        # Final score
        # ----------------------------------------------

        score = (
            rating_score
            + acceptance_score
            + completion_score
            + distance_score
            + workload_score
            + opportunity_score
            + fairness_bonus
            - cancellation_penalty
        )

        # ----------------------------------------------
        # Prevent negative scores
        # ----------------------------------------------

        return max(
            score,
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
        Normalize a percentage/rate to 0–1.

        Supports both:

            0.95
            95

        Examples
        --------
        0.95 → 0.95
        95   → 0.95
        1    → 1
        100  → 1
        """

        value = Decimal(
            str(value or 0)
        )

        if value <= 0:
            return Decimal("0")

        if value > 1:
            value = value / Decimal("100")

        return min(
            value,
            Decimal("1"),
        )