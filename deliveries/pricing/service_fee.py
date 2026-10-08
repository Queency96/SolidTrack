from decimal import Decimal

from .base import PricingStrategy


class ServiceFeeStrategy(PricingStrategy):

    def calculate(
        self,
        config,
    ):

        return Decimal(
            str(config.service_fee)
        ).quantize(
            Decimal("0.01")
        )