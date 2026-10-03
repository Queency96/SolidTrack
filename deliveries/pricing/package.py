from .base import PricingStrategy


class PackagePricingStrategy(PricingStrategy):

    def calculate(self, config, package_size):
        fees = {
            "SMALL": config.small_package_fee,
            "MEDIUM": config.medium_package_fee,
            "LARGE": config.large_package_fee,
        }
        try:
            return fees[package_size]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported package size: {package_size!r}. "
                f"Expected one of {sorted(fees)}."
            ) from exc