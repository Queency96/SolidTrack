from deliveries.dispatch.service import DispatchConfigurationService
from .assignment import AssignmentService
from .exceptions import NoAvailableRider
from .matcher import RiderMatcher
from .notifier import DispatchNotifier
from .scorer import RiderScorer


class DispatchEngine:
    SEARCH_RADII = [3, 5, 8, 10, 15]

    @classmethod
    def dispatch(cls, delivery):
        """
        Automatically assign the best available rider
        for a delivery.
        """
        matches = []

        config = DispatchConfigurationService.get_configuration()

        radius = config.initial_search_radius_km

        while radius <= config.maximum_search_radius_km:

            matches = RiderMatcher.find_nearby_riders(
                delivery=delivery,
                radius_km=radius,
            )

            if matches:
                break

            radius += config.search_radius_increment_km

        if not matches:
            raise NoAvailableRider()

        ranked_matches = sorted(
            matches,
            key=lambda match: RiderScorer.score(
                rider=match["rider"],
                delivery=delivery,
                distance=match["distance"],
            ),
            reverse=True,
        )

        best_match = ranked_matches[0]

        rider = best_match["rider"]

        assignment = AssignmentService.assign(
            delivery=delivery,
            rider=rider,
        )

        DispatchNotifier.notify(
            assignment
        )

        return assignment