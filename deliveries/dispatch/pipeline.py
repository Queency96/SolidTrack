from deliveries.models.delivery import Delivery
from .context import DispatchContext
from .eligibility import RiderEligibilityService
from .exceptions import (
    DispatchConfigurationError,
    NoAvailableRider,
)
from .matcher import RiderMatcher
from .notifier import DispatchNotifier
from .offer import DeliveryOfferService
from .rider_ranker import RiderRanker
from .result import DispatchResult
from .status import DispatchStatus


class DispatchPipeline:
    """
    Executes the automatic rider dispatch workflow.

    Workflow
    --------
    1. Mark delivery as waiting for a rider.
    2. Find nearby eligible riders.
    3. Rank rider matches.
    4. Perform final eligibility validation.
    5. Create a delivery offer.
    6. Notify the selected rider.

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
        • Implement rider ranking logic

    Those responsibilities belong to their respective
    services.

    Architecture
    ------------
    DispatchPipeline
        ↓
    RiderMatcher
        ↓
    RiderMatch
        ↓
    RiderRanker
        ↓
    ranked RiderMatch
        ↓
    DeliveryOfferService
        ↓
    DispatchNotifier

    Rider acceptance/rejection/expiration is handled
    asynchronously by DispatchCoordinator.
    """

    # ==================================================
    # Initialization
    # ==================================================

    def __init__(
        self,
        context: DispatchContext,
    ):
        """
        Initialize the dispatch pipeline.
        """

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

        try:

            # ------------------------------------------
            # Dispatch state
            # ------------------------------------------

            self.context.update_status(
                DispatchStatus.DISPATCHING,
            ).update_step(
                "Dispatch",
            )

            # ------------------------------------------
            # Delivery state
            # ------------------------------------------

            self._set_delivery_waiting_for_rider()

            # ------------------------------------------
            # Find nearby riders
            # ------------------------------------------

            self._find_matches()

            # ------------------------------------------
            # Rank riders
            # ------------------------------------------

            self._rank_matches()

            # ------------------------------------------
            # Create rider offer
            # ------------------------------------------

            self._offer_first_rider()

            # ------------------------------------------
            # Return result
            # ------------------------------------------

            return (
                DispatchResult.success_result(
                    status=self.context.status,
                    message="Delivery offer created.",
                    context=self.context,
                    delivery=self.context.delivery,
                    offer=self.context.offer,
                )
            )

        except (
            DispatchConfigurationError,
            NoAvailableRider,
        ) as exc:

            self.context.update_status(
                DispatchStatus.FAILED,
            )

            self.context.add_error(
                str(exc),
            )

            return (
                DispatchResult.failure_result(
                    status=DispatchStatus.FAILED,
                    message=str(exc),
                    context=self.context,
                    delivery=self.context.delivery,
                    errors=[str(exc)],
                )
            )

        except Exception as exc:

            self.context.update_status(
                DispatchStatus.FAILED,
            )

            self.context.add_error(
                str(exc),
            )

            return (
                DispatchResult.failure_result(
                    status=DispatchStatus.FAILED,
                    message=(
                        "An unexpected error occurred "
                        "during dispatch."
                    ),
                    context=self.context,
                    delivery=self.context.delivery,
                    errors=[str(exc)],
                )
            )

    # ==================================================
    # Delivery State
    # ==================================================

    def _set_delivery_waiting_for_rider(self):
        """
        Mark the delivery as waiting for a rider.

        DELIVERED and CANCELLED deliveries cannot enter
        the dispatch workflow.

        FAILED deliveries remain retryable.
        """

        delivery = self.context.delivery

        # ----------------------------------------------
        # Validate delivery
        # ----------------------------------------------

        if delivery is None:
            raise NoAvailableRider(
                "Delivery is required for dispatch."
            )

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

        self.context.update_step(
            "WaitingForRider",
        )

    # ==================================================
    # Find Riders
    # ==================================================

    def _find_matches(self):
        """
        Search progressively larger geographic
        radii until eligible riders are found.

        RiderMatcher is responsible for:

            • Geographic search
            • Rider eligibility filtering
            • Creating RiderMatch objects

        DispatchPipeline only controls the search
        progression.
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
        # Progressive search
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
                    matches=list(matches),
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
        Rank the RiderMatch objects using RiderRanker.

        RiderRanker owns the actual ranking/scoring
        strategy.

        DispatchPipeline does not calculate scores or
        sort riders itself.
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
        # Rank matches
        # ----------------------------------------------

        ranked_matches = RiderRanker.rank(
            context=self.context,
            matches=matches,
        )

        # ----------------------------------------------
        # Validate ranking result
        # ----------------------------------------------

        if not ranked_matches:
            raise NoAvailableRider(
                "Rider ranking returned no "
                "eligible matches."
            )

        # ----------------------------------------------
        # Store ranking
        # ----------------------------------------------

        self.context.set(
            ranked_matches=list(ranked_matches),
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

        If a ranked rider is no longer eligible:

            1. Exclude the rider.
            2. Remove the rider from the current matches.
            3. Continue to the next ranked rider.

        This prevents a stale rider state from resulting
        in an invalid offer.
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
            # Validate rider
            # ------------------------------------------

            if rider is None:
                continue

            # ------------------------------------------
            # Already excluded
            # ------------------------------------------

            if self.context.is_rider_excluded(
                rider,
            ):
                continue

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

            offer = (
                DeliveryOfferService.create(
                    delivery=self.context.delivery,
                    rider=rider,
                    radius=match.search_radius,
                    timeout=(
                        self.context.config
                        .rider_response_timeout_seconds
                    ),
                )
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

        Notification failure does not delete the offer.

        The offer is already persisted and therefore
        remains available for recovery/monitoring logic.
        """

        try:

            DispatchNotifier.offer_delivery(
                offer,
            )

            self.context.add_metadata(
                "rider_notified",
                True,
            )

            return True

        except Exception as exc:

            self.context.add_metadata(
                "rider_notified",
                False,
            )

            self.context.add_warning(
                "Delivery offer was created, "
                "but rider notification failed."
            )

            self.context.add_error(
                str(exc),
            )

            return False

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
        centralized source of truth.

        The rider is also removed from the current
        match collections.
        """

        if rider_id is None:
            return

        # ----------------------------------------------
        # Central exclusion state
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
            if (
                match.rider is not None
                and match.rider.id != rider_id
            )
        ]

        # ----------------------------------------------
        # Remove from ranked matches
        # ----------------------------------------------

        self.context.ranked_matches = [
            match
            for match in self.context.ranked_matches
            if (
                match.rider is not None
                and match.rider.id != rider_id
            )
        ]