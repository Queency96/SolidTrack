from .maps.factory import MapProviderFactory


class DistanceService:
    """
    Facade for map providers.
    """

    provider = MapProviderFactory.get_provider()

    @classmethod
    def get_distance(
        cls,
        pickup_lat,
        pickup_lng,
        destination_lat,
        destination_lng,
    ):
        return cls.provider.get_distance(
            pickup_lat,
            pickup_lng,
            destination_lat,
            destination_lng,
        )

    @classmethod
    def set_provider(cls, provider):
        """
        Override the provider at runtime if needed.
        """
        cls.provider = provider