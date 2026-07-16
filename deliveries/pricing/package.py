from .base import PricingStrategy


class PackagePricingStrategy(PricingStrategy):

    def calculate(
        self,
        config,
        package_size,
    ):

        fees = {

            "SMALL":
            config.small_package_fee,

            "MEDIUM":
            config.medium_package_fee,

            "LARGE":
            config.large_package_fee,

        }

        return fees[package_size]