from .base import PricingStrategy


class ServiceFeeStrategy(PricingStrategy):

    def calculate(
        self,
        config,
    ):

        return config.service_fee