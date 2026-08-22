from deliveries.models import Delivery

from .context import DispatchContext
from .exceptions import (
    DispatchConfigurationError,
    NoAvailableRider,
)
from .eligibility import RiderEligibilityService
from .matcher import RiderMatcher
from .notifier import DispatchNotifier
from .offer import DeliveryOfferService
from .result import DispatchResult
from .scorer import RiderScorer
from .status import DispatchStatus


class DispatchPipeline:
    """
    Executes the automatic rider dispatch workflow.

    Workflow
    --------
    1. Mark delivery as waiting for a rider.
    2. Find nearby eligible riders.
    3. Calculate rider scores.
    4. Rank riders.
    5. Perform final eligibility validation.
    6. Create a delivery offer.
    7. Notify the selected rider.

    Rider responses are handled asynchronously
    by DispatchCoordinator.

    Responsibilities
    ----------------
    This class coordinates the dispatch process.

    It does NOT:
        • Accept offers
        • Reject offers
        • Assign riders
        • Manage assignment lifecycle
        • Calculate distance
        • Calculate individual rider scores
    """

    # ==================================================
    # Initialization
    # ==================================================

    def __init__(
        self,
        context: DispatchContext,
    ):
        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        self.context = context

    # ==================================================
    # Public API
    # ==================================================

    def run(self):
        """
        Execute the complete dispatch pipeline.

        Returns
        -------
        DispatchResult
            Standardized result containing the
            dispatch context, delivery and offer.
        """

        # ----------------------------------------------
        # Dispatch state
        # ----------------------------------------------

        self.context.update_status(
            DispatchStatus.DISPATCHING,
        ).update_step(
            "Dispatch",
        )

        # ----------------------------------------------
        # Delivery state
        # ----------------------------------------------

        self._set_delivery_waiting_for_rider()

        # ----------------------------------------------
        # Find eligible riders
        # ----------------------------------------------

        self._find_matches()

        # ----------------------------------------------
        # Score and rank riders
        # ----------------------------------------------

        self._rank_matches()

        # ----------------------------------------------
        # Create rider offer
        # ----------------------------------------------

        self._offer_first_rider()

        # ----------------------------------------------
        # Return result
        # ----------------------------------------------

        return DispatchResult.success_result(
            status=self.context.status,
            message="Delivery offer created.",
            context=self.context,
            delivery=self.context.delivery,
            offer=self.context.offer,
        )

    # ==================================================
    # Delivery State
    # ==================================================

    def _set_delivery_waiting_for_rider(self):
        """
        Mark the delivery as waiting for a rider.

        This represents the delivery-level state while
        the dispatch engine searches for and offers the
        delivery to riders.

        DELIVERED and CANCELLED deliveries cannot enter
        the dispatch workflow.
        """

        delivery = self.context.delivery

        # ----------------------------------------------
        # Terminal state validation
        # ----------------------------------------------

        if (
            delivery.status
            == Delivery.DeliveryStatus.DELIVERED
        ):
            raise NoAvailableRider(
                "Cannot dispatch an already "
                "delivered delivery."
            )

        if (
            delivery.status
            == Delivery.DeliveryStatus.CANCELLED
        ):
            raise NoAvailableRider(
                "Cannot dispatch a cancelled delivery."
            )

        # ----------------------------------------------
        # Update delivery state
        # ----------------------------------------------

        delivery.status = (
            Delivery.DeliveryStatus.WAITING_FOR_RIDER
        )

        delivery.save(
            update_fields=[
                "status",
            ],
        )

    # ==================================================
    # Find Riders
    # ==================================================

    def _find_matches(self):
        """
        Search progressively larger geographic
        radii until eligible riders are found.

        The search starts at the configured initial
        radius and expands until the maximum radius
        is reached.
        """

        self.context.update_status(
            DispatchStatus.SEARCHING,
        ).update_step(
            "FindMatches",
        )

        config = self.context.config

        radius = config.initial_search_radius_km
        maximum = config.maximum_search_radius_km
        increment = config.search_radius_increment_km

        # ----------------------------------------------
        # Validate configuration
        # ----------------------------------------------

        if radius <= 0:
            raise DispatchConfigurationError(
                "Initial search radius must be "
                "greater than zero."
            )

        if maximum <= 0:
            raise DispatchConfigurationError(
                "Maximum search radius must be "
                "greater than zero."
            )

        if increment <= 0:
            raise DispatchConfigurationError(
                "Search radius increment must be "
                "greater than zero."
            )

        if maximum < radius:
            raise DispatchConfigurationError(
                "Maximum search radius must be "
                "greater than or equal to the "
                "initial search radius."
            )

        # ----------------------------------------------
        # Progressive geographic search
        # ----------------------------------------------

        while radius <= maximum:

            self.context.update_step(
                f"FindMatches:{radius}km",
            )

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

        # ----------------------------------------------
        # No riders found
        # ----------------------------------------------

        raise NoAvailableRider(
            "No eligible rider found within "
            "the configured search radius."
        )

    # ==================================================
    # Rank Riders
    # ==================================================

    def _rank_matches(self):
        """
        Calculate the dispatch score for every rider
        and rank riders from highest to lowest score.
        """

        self.context.update_step(
            "RankMatches",
        )

        matches = self.context.matches

        # ----------------------------------------------
        # Validate matches
        # ----------------------------------------------

        if not matches:
            raise NoAvailableRider(
                "No rider matches available "
                "for ranking."
            )

        # ----------------------------------------------
        # Score riders
        # ----------------------------------------------

        for match in matches:

            RiderScorer.score(
                context=self.context,
                match=match,
            )

        # ----------------------------------------------
        # Ensure all matches were scored
        # ----------------------------------------------

        unscored = [
            match
            for match in matches
            if not match.is_scored
        ]

        if unscored:
            raise NoAvailableRider(
                "One or more rider matches "
                "could not be scored."
            )

        # ----------------------------------------------
        # Rank riders
        # ----------------------------------------------

        ranked = sorted(
            matches,
            key=lambda match: match.score,
            reverse=True,
        )

        if not ranked:
            raise NoAvailableRider(
                "Unable to rank available riders."
            )

        # ----------------------------------------------
        # Store ranking
        # ----------------------------------------------

        self.context.set(
            ranked_matches=ranked,
        )

        self.context.update_status(
            DispatchStatus.RANKED,
        )

    # ==================================================
    # Create Offer
    # ==================================================

    def _offer_first_rider(self):
        """
        Create an offer for the highest-ranked rider
        who is still eligible.

        A final eligibility check is performed immediately
        before creating the offer because rider state may
        have changed after the initial matching query.

        If a ranked rider is no longer eligible, that rider
        is excluded and the next ranked rider is evaluated.
        """

        self.context.update_step(
            "CreateOffer",
        )

        ranked_matches = (
            self.context.ranked_matches
        )

        # ----------------------------------------------
        # Validate ranked matches
        # ----------------------------------------------

        if not ranked_matches:
            raise NoAvailableRider(
                "No ranked rider is available "
                "for dispatch."
            )

        # ----------------------------------------------
        # Iterate through ranked riders
        # ----------------------------------------------

        for match in ranked_matches:

            rider = match.rider

            # ------------------------------------------
            # Final eligibility validation
            # ------------------------------------------

            if not RiderEligibilityService.is_eligible(
                rider=rider,
                context=self.context,
            ):
                self.context.add_warning(
                    f"Rider {rider.id} is no longer "
                    "eligible for this dispatch."
                )

                self._exclude_rider(
                    rider.id,
                )

                continue

            # ------------------------------------------
            # Create offer
            # ------------------------------------------

            offer = DeliveryOfferService.create(
                delivery=self.context.delivery,
                rider=rider,
                radius=match.search_radius,
                timeout=(
                    self.context.config
                    .rider_response_timeout_seconds
                ),
            )

            # ------------------------------------------
            # Store selected rider
            # ------------------------------------------

            self.context.set(
                selected_rider=rider,
                selected_match=match,
                offer=offer,
            )

            # ------------------------------------------
            # Notify rider
            # ------------------------------------------

            self._notify_rider(
                offer,
            )

            # ------------------------------------------
            # Dispatch state
            # ------------------------------------------

            self.context.update_status(
                DispatchStatus.OFFERED,
            ).update_step(
                "OfferCreated",
            )

            return

        # ----------------------------------------------
        # No eligible rider remains
        # ----------------------------------------------

        raise NoAvailableRider(
            "No eligible rider remains "
            "for dispatch."
        )

    # ==================================================
    # Notification
    # ==================================================

    def _notify_rider(
        self,
        offer,
    ):
        """
        Notify the selected rider.

        Notification failure does not invalidate the
        database offer because the offer has already
        been created successfully.

        The failure is stored as a warning/error on the
        dispatch context.
        """

        try:

            DispatchNotifier.offer_delivery(
                offer,
            )

        except Exception as exc:

            self.context.add_warning(
                "Delivery offer was created, "
                "but rider notification failed."
            )

            self.context.add_error(
                str(exc),
            )

    # ==================================================
    # Rider Exclusion
    # ==================================================

    def _exclude_rider(
        self,
        rider_id,
    ):
        """
        Exclude a rider from the current dispatch
        lifecycle.

        DispatchContext.excluded_rider_ids is the
        single source of truth.

        The rider is also removed from both the current
        match collection and the ranked match collection
        so that the context remains internally consistent.
        """

        if rider_id is None:
            return

        # ----------------------------------------------
        # Update centralized exclusion state
        # ----------------------------------------------

        self.context.exclude_rider_id(
            rider_id,
        )

        # ----------------------------------------------
        # Remove from matches
        # ----------------------------------------------

        self.context.matches = [
            match
            for match in self.context.matches
            if match.rider.id != rider_id
        ]

        # ----------------------------------------------
        # Remove from ranked matches
        # ----------------------------------------------

        self.context.ranked_matches = [
            match
            for match in self.context.ranked_matches
            if match.rider.id != rider_id
        ]