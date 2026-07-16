import openrouteservice
from django.conf import settings
from .base import MapProvider


class OpenRouteServiceProvider(MapProvider):

    def __init__(self):

        self.client = openrouteservice.Client(
            key=settings.OPENROUTESERVICE_API_KEY
        )

    def get_distance(
        self,
        pickup_lat,
        pickup_lng,
        destination_lat,
        destination_lng,
    ):

        route = self.client.directions(

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

            profile="driving-car",

            format="geojson",

        )

        summary = (
            route["features"][0]
            ["properties"]["summary"]
        )

        return {

            "distance_km":
            summary["distance"] / 1000,

            "duration_minutes":
            summary["duration"] / 60,

        }