from decimal import Decimal

from .base import BaseDispatchStrategy


class BalancedDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Balanced rider dispatch strategy.

    Considers:

    • Rider rating
    • Distance from pickup
    • Current workload
    • Acceptance rate
    • Completion rate
    • Cancellation rate
    • Delivery experience

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
        Calculate the total dispatch score.

        Higher scores indicate better rider matches.
        """

        config = context.config

        score = Decimal("0.00")

        score += self._rating_score(
            config,
            match,
        )

        score += self._distance_score(
            config,
            match,
        )

        score += self._workload_score(
            config,
            match,
        )

        score += self._acceptance_rate_score(
            config,
            match,
        )

        score += self._completion_rate_score(
            config,
            match,
        )

        score += self._cancellation_score(
            config,
            match,
        )

        score += self._experience_score(
            config,
            match,
        )

        return score

    # ==================================================
    # Rating
    # ==================================================

    @staticmethod
    def _rating_score(
        config,
        match,
    ) -> Decimal:
        """
        Higher-rated riders receive a higher score.
        """

        return (
            match.rating
            * config.rating_weight
        )

    # ==================================================
    # Distance
    # ==================================================

    @staticmethod
    def _distance_score(
        config,
        match,
    ) -> Decimal:
        """
        Closer riders receive a higher score.

        Distance is treated as a penalty.
        """

        return (
            -match.distance_km
            * config.distance_weight
        )

    # ==================================================
    # Workload
    # ==================================================

    @staticmethod
    def _workload_score(
        config,
        match,
    ) -> Decimal:
        """
        Riders with fewer active deliveries
        receive a higher score.
        """

        return (
            -Decimal(
                str(
                    match.active_delivery_count
                )
            )
            * config.workload_weight
        )

    # ==================================================
    # Acceptance Rate
    # ==================================================

    @staticmethod
    def _acceptance_rate_score(
        config,
        match,
    ) -> Decimal:
        """
        Higher acceptance rates receive
        a higher score.
        """

        return (
            match.acceptance_rate
            * config.acceptance_rate_weight
        )

    # ==================================================
    # Completion Rate
    # ==================================================

    @staticmethod
    def _completion_rate_score(
        config,
        match,
    ) -> Decimal:
        """
        Higher completion rates receive
        a higher score.
        """

        return (
            match.completion_rate
            * config.completion_rate_weight
        )

    # ==================================================
    # Cancellation Rate
    # ==================================================

    @staticmethod
    def _cancellation_score(
        config,
        match,
    ) -> Decimal:
        """
        A higher cancellation rate reduces
        the rider's score.
        """

        return (
            -match.cancellation_rate
            * config.cancellation_weight
        )

    # ==================================================
    # Experience
    # ==================================================

    @staticmethod
    def _experience_score(
        config,
        match,
    ) -> Decimal:
        """
        Reward riders with more completed
        deliveries.
        """

        return (
            Decimal(
                str(
                    match.completed_deliveries
                )
            )
            * config.experience_weight
        )