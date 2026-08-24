from decimal import Decimal
from .base import BaseDispatchStrategy


class ExpressDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Express dispatch strategy.

    Prioritizes the fastest rider for urgent deliveries.

    Positive factors
    ----------------
    • Proximity to pickup
    • High acceptance rate
    • High completion rate
    • High rider rating

    Negative factors
    ----------------
    • Active workload
    • Cancellation rate

    Express dispatch intentionally gives distance a
    stronger influence than the normal balanced strategy.

    All weighting is controlled by DispatchConfiguration.

    RiderMatch provides the normalized rider metrics,
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
        Calculate the express dispatch score.

        Higher scores indicate a better rider for an
        urgent delivery.
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
        # Acceptance Rate
        # ----------------------------------------------

        score += (
            match.acceptance_rate
            * config.acceptance_rate_weight
        )

        # ----------------------------------------------
        # Completion Rate
        # ----------------------------------------------

        score += (
            match.completion_rate
            * config.completion_rate_weight
        )

        # ==================================================
        # Distance
        # ==================================================
        #
        # Distance is the most important factor for
        # express delivery.
        #
        # A shorter distance produces a higher score.

        score -= (
            match.distance
            * config.distance_weight
        )

        # ==================================================
        # Negative Factors
        # ==================================================

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
        # Cancellation Rate
        # ----------------------------------------------

        score -= (
            match.cancellation_rate
            * config.cancellation_weight
        )

        # ==================================================
        # Normalize
        # ==================================================

        return max(
            score,
            Decimal("0"),
        )