from abc import ABC
from abc import abstractmethod


class MapProvider(ABC):

    @abstractmethod
    def get_distance(
        self,
        pickup_lat,
        pickup_lng,
        destination_lat,
        destination_lng,
    ):
        """
        Returns:

        {
            "distance_km": float,
            "duration_minutes": float,
        }
        """
        raise NotImplementedError