from decimal import Decimal
from deliveries.utils import calculate_distance
from .eligibility import RiderEligibilityService


class RiderMatcher:
    DEFAULT_RADIUS_KM = Decimal("5.0")
    @classmethod
    def find_nearby_riders(
        cls,
        delivery,
        radius_km=None,
    ):
        """
        Returns eligible riders ordered by proximity
        to the pickup location.
        """

        if radius_km is None:
            radius_km = cls.DEFAULT_RADIUS_KM

        pickup_lat = delivery.pickup_latitude
        pickup_lng = delivery.pickup_longitude

        nearby_riders = []

        riders = (
            RiderEligibilityService
            .get_available_riders()
            .select_related("location")
        )

        for rider in riders:
            if not hasattr(rider, "location"):
                continue
            distance = Decimal(
                str(
                    calculate_distance(
                        pickup_lat,
                        pickup_lng,
                        rider.location.latitude,
                        rider.location.longitude,
                    )
                )
            )

            if distance <= radius_km:
                nearby_riders.append(
                    {
                        "rider": rider,
                        "distance": distance,
                    }
                )

        nearby_riders.sort(
            key=lambda item: item["distance"]
        )

        return nearby_riders