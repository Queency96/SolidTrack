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

        for radius in cls.SEARCH_RADII:
            matches = RiderMatcher.find_nearby_riders(
                delivery=delivery,
                radius_km=radius,
            )

            if matches:
                break

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