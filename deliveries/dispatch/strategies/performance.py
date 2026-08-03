from decimal import Decimal
from .base import BaseDispatchStrategy


class PerformanceDispatchStrategy(
    BaseDispatchStrategy,
):

    def score(
        self,
        context,
        match,
    ):

        rider = match.rider

        return (
            Decimal(str(rider.rating))
            * Decimal("20")
            + Decimal(
                str(rider.completion_rate)
            )
            * Decimal("10")
            + Decimal(
                str(rider.acceptance_rate)
            )
            * Decimal("5")
        )