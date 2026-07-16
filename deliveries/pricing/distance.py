from decimal import Decimal
from .base import PricingStrategy


class DistancePricingStrategy(PricingStrategy):

    def calculate(
        self,
        config,
        distance,
    ):

        return (
            distance
            * config.price_per_km
        ).quantize(
            Decimal("0.01")
        )