from decimal import Decimal

from .base import PricingStrategy


class InsurancePricingStrategy(PricingStrategy):

    def calculate(
        self,
        config,
        insurance,
        declared_value,
    ):

        if not insurance:
            return Decimal("0.00")

        return (
            Decimal(str(declared_value))
            * config.insurance_rate
        ).quantize(
            Decimal("0.01")
        )