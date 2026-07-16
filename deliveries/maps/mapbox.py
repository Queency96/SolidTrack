from .base import MapProvider


class MapboxProvider(MapProvider):

    def get_distance(
        self,
        pickup_lat,
        pickup_lng,
        destination_lat,
        destination_lng,
    ):

        raise NotImplementedError(
            "Mapbox provider not implemented."
        )