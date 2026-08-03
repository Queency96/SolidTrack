from decimal import Decimal
from .base import BaseDispatchStrategy


class NearestDispatchStrategy(
    BaseDispatchStrategy,
):

    def score(
        self,
        context,
        match,
    ):
        return (
            Decimal("100000")
            - match.distance
        )