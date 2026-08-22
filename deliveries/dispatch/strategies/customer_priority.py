from decimal import Decimal

from .base import BaseDispatchStrategy


class CustomerPriorityDispatchStrategy(BaseDispatchStrategy):
    """
    Customer-priority dispatch strategy.

    This strategy prioritizes riders based on the quality
    of the rider match while giving additional importance
    to customer-facing delivery reliability.

    Scoring priorities
    ------------------
    1. Rider rating
    2. Completion rate
    3. Acceptance rate
    4. Distance
    5. Current workload
    6. Cancellation rate
    7. Rider experience

    The strategy uses the dispatch configuration weights
    rather than hard-coded scoring weights.

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
        Calculate a customer-priority score.

        Customer-priority dispatch favors riders who are
        reliable and likely to complete the delivery
        successfully, while still considering proximity
        and current workload.
        """

        self.validate_inputs(
            context,
            match,
        )

        config = context.config

        # ----------------------------------------------
        # Normalized rider metrics
        # ----------------------------------------------

        rating = self.decimal(
            match.rating,
        )

        acceptance_rate = self.decimal(
            match.acceptance_rate,
        )

        completion_rate = self.decimal(
            match.completion_rate,
        )

        cancellation_rate = self.decimal(
            match.cancellation_rate,
        )

        completed_deliveries = self.decimal(
            match.completed_deliveries,
        )

        distance = self.decimal(
            match.distance_km,
        )

        active_jobs = self.decimal(
            match.active_jobs,
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
        #
        # Rider rating normally ranges from 0–5.
        # Normalize it to 0–1 before applying weight.

        rating_score = (
            rating / Decimal("5")
        ) * rating_weight

        # ----------------------------------------------
        # Acceptance rate
        # ----------------------------------------------
        #
        # Supports both:
        #     0.95
        # and:
        #     95
        #
        # internally normalize to 0–1.

        acceptance = self._normalize_percentage(
            acceptance_rate,
        )

        acceptance_score = (
            acceptance
            * acceptance_weight
        )

        # ----------------------------------------------
        # Completion rate
        # ----------------------------------------------

        completion = self._normalize_percentage(
            completion_rate,
        )

        completion_score = (
            completion
            * completion_weight
        )

        # ----------------------------------------------
        # Cancellation penalty
        # ----------------------------------------------

        cancellation = self._normalize_percentage(
            cancellation_rate,
        )

        cancellation_penalty = (
            cancellation
            * cancellation_weight
        )

        # ----------------------------------------------
        # Distance penalty
        # ----------------------------------------------
        #
        # Closer riders receive higher scores.
        #
        # 0 km   → 1.0
        # 1 km   → 0.5
        # 2 km   → 0.333...
        #
        # This avoids an arbitrary maximum distance.

        distance_factor = (
            Decimal("1")
            / (
                Decimal("1")
                + max(
                    distance,
                    Decimal("0"),
                )
            )
        )

        distance_score = (
            distance_factor
            * distance_weight
        )

        # ----------------------------------------------
        # Workload penalty
        # ----------------------------------------------
        #
        # Riders with fewer active deliveries are
        # preferred.

        workload_factor = (
            Decimal("1")
            / (
                Decimal("1")
                + max(
                    active_jobs,
                    Decimal("0"),
                )
            )
        )

        workload_score = (
            workload_factor
            * workload_weight
        )

        # ----------------------------------------------
        # Experience
        # ----------------------------------------------
        #
        # Use diminishing returns so that a rider with
        # 1,000 completed deliveries does not dominate
        # every other rider purely through experience.

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

        # ----------------------------------------------
        # Customer-priority reliability bonus
        # ----------------------------------------------
        #
        # Customer priority places additional emphasis
        # on successful completion and acceptance.
        #
        # These multipliers intentionally use the
        # configured values instead of introducing new
        # configuration fields.

        reliability_bonus = (
            (
                completion
                * completion_weight
            )
            + (
                acceptance
                * acceptance_weight
            )
        )

        # ----------------------------------------------
        # Final score
        # ----------------------------------------------

        score = (
            rating_score
            + distance_score
            + workload_score
            + completion_score
            + acceptance_score
            + experience_score
            + reliability_bonus
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
        Normalize a percentage/rate to the range 0–1.

        Supported input examples:

            0.95 → 0.95
            95   → 0.95
            1    → 1
            100  → 1

        Values below zero are clamped to zero.
        Values above 100 are clamped to one.
        """

        value = Decimal(
            str(value or 0)
        )

        if value < 0:
            return Decimal("0")

        if value > 1:
            value = value / Decimal("100")

        return min(
            value,
            Decimal("1"),
        )