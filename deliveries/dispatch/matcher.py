from decimal import Decimal
from deliveries.distance_service import DistanceService
from .eligibility import RiderEligibilityService
from .match import RiderMatch


class RiderMatcher:
    """
    Matches eligible riders to a delivery
    based on proximity.
    """

    DEFAULT_RADIUS_KM = Decimal("5.00")

    @classmethod
    def find_nearby_riders(
        cls,
        context,
        radius_km=None,
    ):
        """
        Return RiderMatch objects ordered by
        distance from the pickup location.
        """

        if radius_km is None:
            radius_km = cls.DEFAULT_RADIUS_KM

        delivery = context.delivery

        riders = (
            RiderEligibilityService
            .get_available_riders(
                delivery=delivery,
            )
            .select_related(
                "location",
            )
        )

        matches: list[RiderMatch] = []

        for rider in riders:

            if not hasattr(
                rider,
                "location",
            ):
                continue

            distance = cls._calculate_distance(
                delivery=delivery,
                rider=rider,
            )

            if distance > radius_km:
                continue

            matches.append(
                RiderMatch(
                    rider=rider,
                    distance=distance,
                    search_radius=radius_km,
                )
            )

        matches.sort(
            key=lambda match: match.distance,
        )

        return matches

    # ------------------------------------------
    # Helpers
    # ------------------------------------------

    @staticmethod
    def _calculate_distance(
        delivery,
        rider,
    ):
        """
        Calculate the rider's distance
        from the pickup location.
        """

        distance = (
            DistanceService.calculate_distance(
                pickup_lat=delivery.pickup_latitude,
                pickup_lng=delivery.pickup_longitude,
                destination_lat=rider.location.latitude,
                destination_lng=rider.location.longitude,
            )
        )

        return Decimal(
            str(distance)
        )