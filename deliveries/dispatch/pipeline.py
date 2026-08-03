from .context import DispatchContext
from .exceptions import (
    DispatchConfigurationError,
    NoAvailableRider,
)
from .matcher import RiderMatcher
# from .notifier import DispatchNotifier
from .offer import DeliveryOfferService
from .result import DispatchResult
from .scorer import RiderScorer
from .status import DispatchStatus


class DispatchPipeline:
    """
    Executes the automatic dispatch workflow.

    Workflow
    --------
    1. Find nearby riders
    2. Rank riders
    3. Create delivery offer
    4. Notify rider

    Rider responses are handled asynchronously by
    the DispatchCoordinator.
    """

    def __init__(
        self,
        context: DispatchContext,
    ):
        self.context = context

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def run(self):

        self.context.update_status(
            DispatchStatus.DISPATCHING,
        )

        self._find_matches()

        self._rank_matches()

        self._offer_first_rider()

        return DispatchResult.success_result(
            status=self.context.status,
            message="Delivery offer created.",
            context=self.context,
            delivery=self.context.delivery,
            offer=self.context.offer,
        )

    # --------------------------------------------------
    # Find Riders
    # --------------------------------------------------

    def _find_matches(self):

        self.context.update_status(
            DispatchStatus.SEARCHING,
        ).update_step(
            "FindMatches",
        )

        radius = (
            self.context.config
            .initial_search_radius_km
        )

        maximum = (
            self.context.config
            .maximum_search_radius_km
        )

        increment = (
            self.context.config
            .search_radius_increment_km
        )

        if increment <= 0:
            raise DispatchConfigurationError(
                "Search radius increment must be greater than zero."
            )

        while radius <= maximum:

            matches = (
                RiderMatcher.find_nearby_riders(
                    context=self.context,
                    radius_km=radius,
                )
            )

            if matches:

                self.context.set(
                    search_radius=radius,
                    matches=matches,
                )

                self.context.update_status(
                    DispatchStatus.MATCHED,
                )

                return

            radius += increment

        raise NoAvailableRider()

    # --------------------------------------------------
    # Rank Riders
    # --------------------------------------------------

    def _rank_matches(self):

        self.context.update_step(
            "RankMatches",
        )

        for match in self.context.matches:
            RiderScorer.score(
                self.context,
                match,
            )

        ranked = sorted(
            self.context.matches,
            key=lambda match: match.score,
            reverse=True,
        )

        self.context.set(
            ranked_matches=ranked,
        )

        self.context.update_status(
            DispatchStatus.RANKED,
        )

    # --------------------------------------------------
    # Offer First Rider
    # --------------------------------------------------

    def _offer_first_rider(self):

        self.context.update_step(
            "CreateOffer",
        )

        best_match = (
            self.context.ranked_matches[0]
        )

        offer = (
            DeliveryOfferService.create_offer(
                delivery=self.context.delivery,
                rider=best_match.rider,
                radius=best_match.search_radius,
                timeout=(
                    self.context.config
                    .rider_response_timeout_seconds
                ),
            )
        )

        DispatchNotifier.offer_delivery(
            offer,
        )

        self.context.set(
            selected_rider=best_match.rider,
            offer=offer,
        )

        self.context.update_status(
            DispatchStatus.OFFERED,
        )