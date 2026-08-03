from decimal import Decimal
from .base import BaseDispatchStrategy


class BalancedDispatchStrategy(
    BaseDispatchStrategy,
):

    def score(
        self,
        context,
        match,
    ):

        config = context.config

        score = Decimal("0")

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