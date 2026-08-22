from django.db import transaction
from notifications.services import NotificationService
from decimal import Decimal
from .pricing import *
from .utils import calculate_distance
from .models import (
    Delivery,
    Package,
    DeliveryAddress,
)
import openrouteservice
from django.conf import settings
from django.core.cache import cache
from .models import PricingConfiguration
from .distance_service import DistanceService
from .pricing.calculator import PricingCalculator
from deliveries.dispatch.coordinator import DispatchCoordinator


class DeliveryService:

    @staticmethod
    @transaction.atomic
    def create_delivery(
        customer,
        validated_data,
    ):

        package_data = validated_data.pop(
            "package"
        )

        pickup_data = validated_data.pop(
            "pickup"
        )

        destination_data = validated_data.pop(
            "destination"
        )

        delivery = Delivery.objects.create(
            customer=customer,
            **validated_data,
        )

        Package.objects.create(
            delivery=delivery,
            **package_data,
        )

        DeliveryAddress.objects.create(
            delivery=delivery,
            address_type=DeliveryAddress.AddressType.PICKUP,
            **pickup_data,
        )

        DeliveryAddress.objects.create(
            delivery=delivery,
            address_type=DeliveryAddress.AddressType.DELIVERY,
            **destination_data,
        )

        # Start the delivery workflow.
        DispatchCoordinator.delivery_created(
            delivery
        )

        return delivery

class DistanceService:

    client = openrouteservice.Client(
        key=settings.OPENROUTESERVICE_API_KEY
    )

    @classmethod
    def get_distance(
        cls,
        pickup_lat,
        pickup_lng,
        destination_lat,
        destination_lng,
    ):

        route = cls.client.directions(
            coordinates=[
                (float(pickup_lng), float(pickup_lat)),
                (float(destination_lng), float(destination_lat)),
            ],
            profile="driving-car",
            format="geojson",
        )

        summary = route["features"][0]["properties"]["summary"]

        return {
            "distance_km": summary["distance"] / 1000,
            "duration_minutes": summary["duration"] / 60,
        }




class PricingService:

    @staticmethod
    def get_configuration():
        """
        Returns the active pricing configuration.
        Cached for 30 minutes.
        """
        config = cache.get("pricing_config")

        if config:
            return config

        config = (
            PricingConfiguration.objects
            .filter(is_active=True)
            .first()
        )

        if config is None:
            raise ValueError(
                "No active pricing configuration found."
            )

        cache.set(
            "pricing_config",
            config,
            timeout=60 * 30,
        )

        return config

    @staticmethod
    def _get_route(data):
        """
        Retrieve driving distance and duration from
        the configured map provider.
        """

        route = DistanceService.get_distance(
            pickup_lat=data["pickup_latitude"],
            pickup_lng=data["pickup_longitude"],
            destination_lat=data["destination_latitude"],
            destination_lng=data["destination_longitude"],
        )

        return {
            "distance": Decimal(
                str(route["distance_km"])
            ),
            "duration": Decimal(
                str(route["duration_minutes"])
            ),
        }

    @staticmethod
    def estimate(
        data,
        customer=None,
        coupon=None,
    ):
        """
        Estimate the delivery price.
        """

        config = PricingService.get_configuration()

        route = PricingService._get_route(data)

        calculator = PricingCalculator()

        result = calculator.calculate(
            config=config,
            distance=route["distance"],
            package_size=data["package_size"],
            vehicle_type=data["vehicle_type"],
            insurance=data.get(
                "insurance",
                False,
            ),
            declared_value=data.get(
                "declared_value",
                0,
            ),
            customer=customer,
            coupon=coupon,
        )

        result.update(
            {
                "distance_km": route["distance"],
                "estimated_duration_minutes": route["duration"],
            }
        )
        return result