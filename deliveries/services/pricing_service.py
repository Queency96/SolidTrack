from decimal import Decimal
from django.core.cache import cache
from ..models import PricingConfiguration
from ..distance_service import DistanceService
from ..pricing.calculator import PricingCalculator


class PricingService:
    """
    Delivery pricing service.

    Responsible for:

        - loading active pricing configuration
        - calculating road distance
        - calculating delivery duration
        - delegating price calculation to PricingCalculator
    """

    CACHE_KEY = "pricing_config"

    CACHE_TIMEOUT = 60 * 30

    # ==================================================
    # Configuration
    # ==================================================

    @classmethod
    def get_configuration(cls):
        """
        Return the active pricing configuration.

        Configuration is cached for 30 minutes.
        """

        config = cache.get(
            cls.CACHE_KEY
        )

        if config is not None:

            return config

        config = (
            PricingConfiguration.objects
            .filter(
                is_active=True,
            )
            .first()
        )

        if config is None:

            raise ValueError(
                "No active pricing configuration found."
            )

        cache.set(
            cls.CACHE_KEY,
            config,
            timeout=cls.CACHE_TIMEOUT,
        )

        return config

    # ==================================================
    # Cache Invalidation
    # ==================================================

    @classmethod
    def clear_configuration_cache(cls):

        cache.delete(
            cls.CACHE_KEY
        )

    # ==================================================
    # Route
    # ==================================================

    @staticmethod
    def _get_route(data):
        """
        Calculate the road route.
        """

        required_fields = [
            "pickup_latitude",
            "pickup_longitude",
            "destination_latitude",
            "destination_longitude",
        ]

        missing = [
            field
            for field in required_fields
            if data.get(field) is None
        ]

        if missing:

            raise ValueError(
                "Missing route coordinates: "
                + ", ".join(missing)
            )

        route = DistanceService.get_distance(
            pickup_lat=data[
                "pickup_latitude"
            ],
            pickup_lng=data[
                "pickup_longitude"
            ],
            destination_lat=data[
                "destination_latitude"
            ],
            destination_lng=data[
                "destination_longitude"
            ],
        )

        return {
            "distance": Decimal(
                str(route["distance_km"])
            ),
            "duration": Decimal(
                str(route["duration_minutes"])
            ),
        }

    # ==================================================
    # Estimate
    # ==================================================

    @classmethod
    def estimate(
        cls,
        data,
        customer=None,
        coupon=None,
    ):
        """
        Estimate a delivery price.

        Expected data:

            {
                "pickup_latitude": ...,
                "pickup_longitude": ...,
                "destination_latitude": ...,
                "destination_longitude": ...,
                "package_size": ...,
                "vehicle_type": ...,
                "insurance": ...,
                "declared_value": ...,
            }
        """

        config = cls.get_configuration()

        route = cls._get_route(
            data
        )

        calculator = PricingCalculator()

        result = calculator.calculate(
            config=config,

            distance=route[
                "distance"
            ],

            package_size=data[
                "package_size"
            ],

            vehicle_type=data[
                "vehicle_type"
            ],

            insurance=data.get(
                "insurance",
                False,
            ),

            declared_value=data.get(
                "declared_value",
                Decimal("0.00"),
            ),

            customer=customer,

            coupon=coupon,
        )

        result.update(
            {
                "distance_km": route[
                    "distance"
                ],

                "estimated_duration_minutes": (
                    route["duration"]
                ),
            }
        )

        return result

    # ==================================================
    # Estimate From Delivery
    # ==================================================

    @classmethod
    def estimate_delivery(
        cls,
        delivery,
        customer=None,
        coupon=None,
    ):
        """
        Calculate pricing using an existing Delivery.

        The delivery must already have pickup and
        destination addresses.
        """

        pickup = delivery.pickup_location

        destination = (
            delivery.destination_location
        )

        if not pickup:

            raise ValueError(
                "Delivery does not have a pickup location."
            )

        if not destination:

            raise ValueError(
                "Delivery does not have a destination."
            )

        package_size = (
            delivery.total_package_weight
        )

        data = {
            "pickup_latitude": pickup[
                "latitude"
            ],

            "pickup_longitude": pickup[
                "longitude"
            ],

            "destination_latitude": destination[
                "latitude"
            ],

            "destination_longitude": destination[
                "longitude"
            ],

            "package_size": package_size,

            "vehicle_type": delivery.vehicle_type,

            "insurance": (
                delivery.insurance_fee
                > Decimal("0.00")
            ),

            "declared_value": Decimal(
                "0.00"
            ),
        }

        return cls.estimate(
            data=data,
            customer=customer,
            coupon=coupon,
        )