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
        """
        Return RiderMatch objects ordered by distance
        from the delivery pickup location.

        Rider eligibility is handled by
        RiderEligibilityService.

        Distance calculation is handled by
        DistanceService.

        Rider scoring is handled later by
        RiderScorer.
        """

        if radius_km is None:
            radius_km = cls.DEFAULT_RADIUS_KM

        radius_km = Decimal(
            str(radius_km)
        )

        if radius_km <= 0:
            return []

        delivery = context.delivery

        # ------------------------------------------
        # Get eligible riders
        # ------------------------------------------

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

        # ------------------------------------------
        # Match riders
        # ------------------------------------------

        for rider in riders:

            # --------------------------------------
            # Exclude previously attempted riders
            # --------------------------------------

            if cls._should_skip_rider(
                context=context,
                rider=rider,
            ):
                continue

            # --------------------------------------
            # Rider location
            # --------------------------------------

            location = getattr(
                rider,
                "location",
                None,
            )

            if location is None:
                continue

            # --------------------------------------
            # Calculate distance
            # --------------------------------------

            distance = cls._calculate_distance(
                delivery=delivery,
                rider=rider,
            )

            # --------------------------------------
            # Radius filter
            # --------------------------------------

            if distance > radius_km:
                continue

            # --------------------------------------
            # Active workload
            # --------------------------------------

            active_delivery_count = int(
                getattr(
                    rider,
                    "active_delivery_count",
                    0,
                )
                or 0
            )

            # --------------------------------------
            # Create RiderMatch
            # --------------------------------------

            match = RiderMatch(
                rider=rider,
                distance=distance,
                search_radius=radius_km,
                active_delivery_count=(
                    active_delivery_count
                ),
            )

            matches.append(
                match,
            )

        # ------------------------------------------
        # Nearest first
        # ------------------------------------------

        matches.sort(
            key=lambda match: match.distance,
        )

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
        """
        Determine whether a rider should be excluded
        from the current dispatch attempt.
        """

        return context.is_rider_excluded(
            rider,
        )

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
        """

        location = getattr(
            rider,
            "location",
            None,
        )

        if location is None:
            raise ValueError(
                "Cannot calculate rider distance "
                "without a rider location."
            )

        distance = (
            DistanceService.calculate_distance(
                pickup_lat=(
                    delivery.pickup_latitude
                ),
                pickup_lng=(
                    delivery.pickup_longitude
                ),
                destination_lat=(
                    location.latitude
                ),
                destination_lng=(
                    location.longitude
                ),
            )
        )

        return Decimal(
            str(distance)
        )