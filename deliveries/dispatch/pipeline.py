from .assignment import AssignmentService
from .exceptions import (
    DispatchConfigurationError,
    NoAvailableRider,
)
from .matcher import RiderMatcher
from .notifier import DispatchNotifier
from .offer import DeliveryOfferService
from .response import DispatchResponseService
from .scorer import RiderScorer
from .service import DispatchConfigurationService


class DispatchPipeline:
    """
    Coordinates the complete dispatch workflow.

    Workflow
    --------
    1. Load dispatch configuration
    2. Find nearby riders
    3. Rank riders
    4. Create delivery offers
    5. Send offer notification
    6. Wait for rider response
    7. Assign rider
    8. Notify customer
    """
    def __init__(self, delivery):
        self.delivery = delivery
        self.config = (
            DispatchConfigurationService
            .get_configuration()
        )
        self.matches = []
        self.ranked_matches = []
        self.assignment = None

    # -------------------------------------
    # Public API
    # -------------------------------------
    def run(self):
        self._find_matches()
        self._rank_matches()
        self._offer_to_riders()
        return self.assignment

    # -------------------------------------
    # Find Nearby Riders
    # -------------------------------------
    def _find_matches(self):
        radius = (
            self.config.initial_search_radius_km
        )
        maximum = (
            self.config.maximum_search_radius_km
        )
        increment = (
            self.config.search_radius_increment_km
        )
        if increment <= 0:
            raise DispatchConfigurationError(
                "Search radius increment must be greater than zero."
            )
        while radius <= maximum:
            self.matches = (
                RiderMatcher.find_nearby_riders(
                    delivery=self.delivery,
                    radius_km=radius,
                )
            )
            if self.matches:
                for match in self.matches:
                    match["search_radius"] = radius
                return
            radius += increment
        raise NoAvailableRider()

    # -------------------------------------
    # Rank Riders
    # -------------------------------------
    def _rank_matches(self):
        self.ranked_matches = sorted(
            self.matches,
            key=lambda match: RiderScorer.score(
                rider=match["rider"],
                delivery=self.delivery,
                distance=match["distance"],
            ),
            reverse=True,
        )

    # -------------------------------------
    # Offer Delivery
    # -------------------------------------
    def _offer_to_riders(self):
        timeout = (
            self.config
            .rider_response_timeout_seconds
        )
        for match in self.ranked_matches:
            rider = match["rider"]
            offer = (
                DeliveryOfferService.create_offer(
                    delivery=self.delivery,
                    rider=rider,
                    radius=match["search_radius"],
                    timeout=timeout,
                )
            )
            DispatchNotifier.offer_delivery(
                offer
            )
            accepted = (
                DispatchResponseService
                .wait_for_response(
                    offer=offer,
                    timeout=timeout,
                )
            )
            if not accepted:
                continue
            self.assignment = (
                AssignmentService.assign(
                    delivery=self.delivery,
                    rider=rider,
                )
            )
            DispatchNotifier.notify_customer(
                self.assignment
            )
            return
        raise NoAvailableRider(
            "All riders rejected or timed out."
        )