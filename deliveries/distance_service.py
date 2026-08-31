from decimal import Decimal
import openrouteservice
from django.conf import settings


class DistanceService:
    """
    Provides road distance and estimated travel duration
    using OpenRouteService.
    """

    profile = "driving-car"

    @classmethod
    def _get_client(cls):

        api_key = getattr(
            settings,
            "OPENROUTESERVICE_API_KEY",
            None,
        )

        if not api_key:

            raise ValueError(
                "OPENROUTESERVICE_API_KEY is not configured."
            )

        return openrouteservice.Client(
            key=api_key,
        )

    @classmethod
    def get_distance(
        cls,
        pickup_lat,
        pickup_lng,
        destination_lat,
        destination_lng,
    ):
        """
        Calculate road distance and estimated duration.

        Returns:

            {
                "distance_km": Decimal,
                "duration_minutes": Decimal,
            }
        """

        if any(
            value is None
            for value in [
                pickup_lat,
                pickup_lng,
                destination_lat,
                destination_lng,
            ]
        ):

            raise ValueError(
                "Pickup and destination coordinates "
                "are required."
            )

        client = cls._get_client()

        route = client.directions(
            coordinates=[
                (
                    float(pickup_lng),
                    float(pickup_lat),
                ),
                (
                    float(destination_lng),
                    float(destination_lat),
                ),
            ],
            profile=cls.profile,
            format="geojson",
        )

        try:

            summary = (
                route["features"][0]
                ["properties"]
                ["summary"]
            )

        except (
            KeyError,
            IndexError,
            TypeError,
        ):

            raise ValueError(
                "Unable to calculate the delivery route."
            )

        return {
            "distance_km": Decimal(
                str(summary["distance"] / 1000)
            ),
            "duration_minutes": Decimal(
                str(summary["duration"] / 60)
            ),
        }