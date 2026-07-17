from deliveries.dispatch.service import DispatchConfigurationService
from .assignment import AssignmentService
from .exceptions import NoAvailableRider, DispatchConfigurationError
from .matcher import RiderMatcher
from .notifier import DispatchNotifier
from .scorer import RiderScorer


class DispatchEngine:
    @classmethod
    def dispatch(cls, delivery):
        """
        Automatically assign the best rider.
        """
        config = (
            DispatchConfigurationService
            .get_configuration()
        )
        radius = config.initial_search_radius_km
        max_radius = config.maximum_search_radius_km
        increment = config.search_radius_increment_km
        if increment <= 0:
            raise DispatchConfigurationError(
                "Search radius increment must be greater than zero."
            )
        matches = []
        while radius <= max_radius:
            matches = RiderMatcher.find_nearby_riders(
                delivery=delivery,
                radius_km=radius,
            )
            if matches:
                for match in matches:
                    match["search_radius"] = radius
                break
            radius += increment
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
        assignment = AssignmentService.assign(
            delivery=delivery,
            rider=best_match["rider"],
        )
        DispatchNotifier.notify(
            assignment
        )

        return assignment