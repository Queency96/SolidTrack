from decimal import Decimal

from .base import PricingStrategy


class VehiclePricingStrategy(PricingStrategy):

    def calculate(
        self,
        config,
        vehicle_type,
    ):

        multipliers = {
            "BIKE": config.bike_multiplier,
            "CAR": config.car_multiplier,
            "VAN": config.van_multiplier,
            "TRUCK": config.truck_multiplier,
        }

        if vehicle_type is None:
            raise ValueError(
                "vehicle_type is required."
            )

        try:
            return multipliers[vehicle_type]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported vehicle type: {vehicle_type!r}. "
                f"Expected one of {sorted(multipliers)}."
            ) from exc