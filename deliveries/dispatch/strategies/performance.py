from decimal import Decimal
from .base import BaseDispatchStrategy


class PerformanceDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Performance-focused dispatch strategy.

    Prioritizes rider performance over proximity.

    Positive factors
    ----------------
    • Rider rating
    • Completion rate
    • Acceptance rate

    Negative factors
    ----------------
    • Cancellation rate
    • Active workload
    • Distance from pickup

    The actual weighting is controlled by
    DispatchConfiguration.

    RiderMatch provides normalized rider metrics,
    so this strategy does not access Django models
    directly.
    """

    # ==================================================
    # Main Scoring Method
    # ==================================================

    def score(
        self,
        context,
        match,
    ) -> Decimal:
        """
        Calculate the performance-based dispatch score.

        Higher scores indicate better-performing riders.
        """

        self.validate_inputs(
            context=context,
            match=match,
        )

        config = context.config

        score = Decimal("0.00")

        # ==================================================
        # Positive Factors
        # ==================================================

        # ----------------------------------------------
        # Rider Rating
        # ----------------------------------------------

        score += (
            match.rating
            * config.rating_weight
        )

        # ----------------------------------------------
        # Completion Rate
        # ----------------------------------------------

        score += (
            match.completion_rate
            * config.completion_rate_weight
        )

        # ----------------------------------------------
        # Acceptance Rate
        # ----------------------------------------------

        score += (
            match.acceptance_rate
            * config.acceptance_rate_weight
        )

        # ==================================================
        # Negative Factors
        # ==================================================

        # ----------------------------------------------
        # Cancellation Rate
        # ----------------------------------------------

        score -= (
            match.cancellation_rate
            * config.cancellation_weight
        )

        # ----------------------------------------------
        # Active Workload
        # ----------------------------------------------

        score -= (
            Decimal(
                str(
                    match.active_delivery_count
                )
            )
            * config.workload_weight
        )

        # ----------------------------------------------
        # Distance
        # ----------------------------------------------

        score -= (
            match.distance
            * config.distance_weight
        )

        return max(
            score,
            Decimal("0"),
        )