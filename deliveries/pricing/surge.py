from decimal import Decimal

from .base import PricingStrategy


class SurgePricingStrategy(PricingStrategy):

    def calculate(
        self,
        config,
        subtotal,
    ):

        if not config.enable_surge:

            return Decimal("0.00")

        return (
            subtotal
            * (
                config.surge_multiplier
                - Decimal("1")
            )
        ).quantize(
            Decimal("0.01")
        )