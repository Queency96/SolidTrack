from .base import PricingStrategy


class VehiclePricingStrategy(PricingStrategy):

    def calculate(
        self,
        config,
        vehicle_type,
    ):

        multipliers = {

            "BIKE":
            config.bike_multiplier,

            "CAR":
            config.car_multiplier,

            "VAN":
            config.van_multiplier,

            "TRUCK":
            config.truck_multiplier,

        }

        return multipliers[vehicle_type]