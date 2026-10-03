from decimal import Decimal
from deliveries.distance_service import DistanceService
from .eligibility import RiderEligibilityService
from .match import RiderMatch


class RiderMatcher:
    """
    Matches eligible riders to a delivery.

    Responsibilities
    ----------------
    • Retrieve eligible riders
    • Calculate rider-to-pickup distance
    • Filter riders outside the search radius
    • Exclude riders that should not receive another offer
    • Return RiderMatch objects
    • Order matches by proximity

    The matcher does NOT:
    • Score riders
    • Create offers
    • Assign riders
    """

    DEFAULT_RADIUS_KM = Decimal("5.00")

    # ==================================================
    # Find Nearby Riders
    # ==================================================

    @classmethod
    def find_nearby_riders(
        cls,
        context,
        radius_km=None,
    ):
        if radius_km is None:
            radius_km = cls.DEFAULT_RADIUS_KM

        radius_km = Decimal(str(radius_km))

        if radius_km <= 0:
            return []

        delivery = context.delivery

        riders = (
            RiderEligibilityService
            .get_available_riders(
                context=context,
                delivery=delivery,
            )
            .select_related(
                "location",
                "rider_profile",
                "rider_statistics",
            )
        )

        matches = []

        for rider in riders:

            if cls._should_skip_rider(context=context, rider=rider):
                continue

            location = getattr(rider, "location", None)

            if location is None:
                continue

            distance = cls._calculate_distance(
                delivery=delivery,
                rider=rider,
            )

            if distance > radius_km:
                continue

            active_delivery_count = int(
                getattr(rider, "active_delivery_count", 0) or 0
            )

            # NOTE: RiderMatch uses `distance_km`, not `distance`.
            match = RiderMatch(
                rider=rider,
                distance_km=distance,
                search_radius=radius_km,
                active_delivery_count=active_delivery_count,
            )

            matches.append(match)

        matches.sort(key=lambda match: match.distance_km)

        return matches

    # ==================================================
    # Skip Rider
    # ==================================================

    @classmethod
    def _should_skip_rider(
        cls,
        context,
        rider,
    ):
        return context.is_rider_excluded(rider)

    # ==================================================
    # Calculate Distance
    # ==================================================

    @staticmethod
    def _calculate_distance(
        delivery,
        rider,
    ):
        """
        Calculate the distance between the rider
        and the delivery pickup location.

        Pickup coordinates come from the delivery's
        pickup address, not from the Delivery row itself.
        """

        location = getattr(rider, "location", None)

        if location is None:
            raise ValueError(
                "Cannot calculate rider distance "
                "without a rider location."
            )

        pickup = delivery.pickup_location

        if not pickup:
            raise ValueError(
                "Cannot calculate rider distance without "
                "a pickup location on the delivery."
            )

        distance = DistanceService.calculate_distance(
            pickup_lat=pickup["latitude"],
            pickup_lng=pickup["longitude"],
            destination_lat=location.latitude,
            destination_lng=location.longitude,
        )

        return Decimal(str(distance))