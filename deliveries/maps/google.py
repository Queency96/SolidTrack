from .base import MapProvider


class GoogleMapsProvider(MapProvider):

    def get_distance(
        self,
        pickup_lat,
        pickup_lng,
        destination_lat,
        destination_lng,
    ):

        raise NotImplementedError(
            "Google Maps provider not implemented."
        )