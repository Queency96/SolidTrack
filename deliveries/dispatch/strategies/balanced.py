from decimal import Decimal
from .base import BaseDispatchStrategy


class BalancedDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Balanced rider dispatch strategy.

    Considers:

        • Rider rating
        • Distance
        • Current workload
        • Acceptance rate
        • Completion rate
        • Cancellation rate
        • Delivery experience

    RiderMatch provides normalized rider metrics.

    This strategy does not access Django models
    directly.
    """

    def score(
        self,
        context,
        match,
    ) -> Decimal:

        self.validate_inputs(
            context,
            match,
        )

        config = context.config

        # ----------------------------------------------
        # Calculate components
        # ----------------------------------------------

        rating = self._rating_score(
            config,
            match,
        )

        distance = self._distance_score(
            config,
            match,
        )

        workload = self._workload_score(
            config,
            match,
        )

        acceptance = (
            self._acceptance_rate_score(
                config,
                match,
            )
        )

        completion = (
            self._completion_rate_score(
                config,
                match,
            )
        )

        cancellation = (
            self._cancellation_score(
                config,
                match,
            )
        )

        experience = (
            self._experience_score(
                config,
                match,
            )
        )

        # ----------------------------------------------
        # Total
        # ----------------------------------------------

        total = (
            rating
            + distance
            + workload
            + acceptance
            + completion
            + cancellation
            + experience
        )

        # ----------------------------------------------
        # Store breakdown
        # ----------------------------------------------

        match.score_breakdown = {
            "rating": rating,
            "distance": distance,
            "workload": workload,
            "acceptance_rate": acceptance,
            "completion_rate": completion,
            "cancellation_rate": cancellation,
            "experience": experience,
            "total": total,
        }

        return total

    # ==================================================
    # Components
    # ==================================================

    @staticmethod
    def _rating_score(
        config,
        match,
    ):
        return (
            match.rating
            * config.rating_weight
        )

    @staticmethod
    def _distance_score(
        config,
        match,
    ):
        return (
            -match.distance
            * config.distance_weight
        )

    @staticmethod
    def _workload_score(
        config,
        match,
    ):
        return (
            -Decimal(
                str(
                    match.active_delivery_count,
                ),
            )
            * config.workload_weight
        )

    @staticmethod
    def _acceptance_rate_score(
        config,
        match,
    ):
        return (
            match.acceptance_rate
            * config.acceptance_rate_weight
        )

    @staticmethod
    def _completion_rate_score(
        config,
        match,
    ):
        return (
            match.completion_rate
            * config.completion_rate_weight
        )

    @staticmethod
    def _cancellation_score(
        config,
        match,
    ):
        return (
            -match.cancellation_rate
            * config.cancellation_weight
        )

    @staticmethod
    def _experience_score(
        config,
        match,
    ):
        return (
            Decimal(
                str(
                    match.completed_deliveries,
                ),
            )
            * config.experience_weight
        )