from decimal import Decimal, InvalidOperation

from django.utils import timezone

from deliveries.models.delivery import Delivery

from .context import DispatchContext
from .eligibility import RiderEligibilityService
from .exceptions import (
    DispatchConfigurationError,
    InvalidOfferState,
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
    1. Validate dispatch context.
    2. Validate dispatch configuration.
    3. Prepare the current dispatch attempt.
    4. Move delivery into WAITING_FOR_RIDER.
    5. Find nearby eligible riders.
    6. Rank rider matches.
    7. Perform final rider eligibility validation.
    8. Create ONE delivery offer.
    9. Notify the selected rider.
    10. Return a DispatchResult.

    Rider responses are NOT handled here.

    Rider responses are handled asynchronously by
    DispatchCoordinator.

    Responsibilities
    ----------------
    DispatchPipeline coordinates the dispatch workflow.

    It does NOT:

        • Accept offers
        • Reject offers
        • Expire offers
        • Cancel offers
        • Assign riders
        • Manage assignment lifecycle
        • Calculate distances
        • Calculate individual rider scores
        • Implement rider ranking logic
        • Persist dispatch history
        • Manage rider availability directly

    Those responsibilities belong to their respective
    services.

    Architecture
    ------------

        DispatchCoordinator
                ↓
        DispatchContext
                ↓
        DispatchPipeline
                ↓
        RiderMatcher
                ↓
        RiderMatch
                ↓
        RiderRanker
                ↓
        RiderEligibilityService
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
            Standardized dispatch result containing:

                • dispatch status
                • dispatch context
                • delivery
                • created offer
                • errors
                • warnings
        """

        try:

            # ------------------------------------------
            # Validate context
            # ------------------------------------------

            self._validate_context()

            # ------------------------------------------
            # Validate configuration
            # ------------------------------------------

            self._validate_configuration()

            # ------------------------------------------
            # Prepare attempt
            # ------------------------------------------

            self._prepare_attempt()

            # ------------------------------------------
            # Dispatch state
            # ------------------------------------------

            self.context.update_status(
                DispatchStatus.DISPATCHING,
            ).update_step(
                "Dispatch",
            )

            # ------------------------------------------
            # Move delivery into waiting state
            # ------------------------------------------

            self._set_delivery_waiting_for_rider()

            # ------------------------------------------
            # Find riders
            # ------------------------------------------

            self._find_matches()

            # ------------------------------------------
            # Rank riders
            # ------------------------------------------

            self._rank_matches()

            # ------------------------------------------
            # Create offer
            # ------------------------------------------

            self._offer_first_rider()

            # ------------------------------------------
            # Final result
            # ------------------------------------------

            return DispatchResult.success_result(
                status=self.context.status,
                message="Delivery offer created.",
                context=self.context,
                delivery=self.context.delivery,
                offer=self.context.offer,
            )

        except (
            DispatchConfigurationError,
            NoAvailableRider,
            InvalidOfferState,
        ) as exc:

            self._fail_context(
                exc,
            )

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                context=self.context,
                delivery=self.context.delivery,
                offer=self.context.offer,
                errors=[
                    str(exc),
                ],
            )

        except Exception as exc:

            self._fail_context(
                exc,
            )

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=(
                    "An unexpected error occurred "
                    "during dispatch."
                ),
                context=self.context,
                delivery=self.context.delivery,
                offer=self.context.offer,
                errors=[
                    str(exc),
                ],
            )

    # ==================================================
    # Attempt Preparation
    # ==================================================

    def _prepare_attempt(self):
        """
        Prepare the context for a new dispatch attempt.

        DispatchContext represents only the current
        in-memory dispatch attempt.

        Persistent history remains stored in the database.
        """

        if self.context.attempt < 1:
            self.context.attempt = 1

        # ----------------------------------------------
        # Clear transient state
        # ----------------------------------------------

        self.context.selected_rider = None
        self.context.selected_match = None
        self.context.offer = None
        self.context.assignment = None

        # ----------------------------------------------
        # Clear current search state
        # ----------------------------------------------

        self.context.clear_matches()

        self.context.search_radius = Decimal("0")

        # ----------------------------------------------
        # Metadata
        # ----------------------------------------------

        self.context.add_metadata(
            "dispatch_attempt",
            self.context.attempt,
        )

        self.context.add_metadata(
            "dispatch_started_at",
            timezone.now(),
        )

        self.context.add_metadata(
            "rider_notified",
            False,
        )

        self.context.add_metadata(
            "offer_created",
            False,
        )

    # ==================================================
    # Context Validation
    # ==================================================

    def _validate_context(self):
        """
        Validate the minimum context required by the
        dispatch pipeline.
        """

        if self.context is None:
            raise DispatchConfigurationError(
                "Dispatch context is required."
            )

        if self.context.delivery is None:
            raise DispatchConfigurationError(
                "Delivery is required for dispatch."
            )

        if self.context.config is None:
            raise DispatchConfigurationError(
                "Dispatch configuration is required."
            )

    # ==================================================
    # Configuration Validation
    # ==================================================

    def _validate_configuration(self):
        """
        Validate dispatch configuration before searching
        for riders.
        """

        config = self.context.config

        # ----------------------------------------------
        # Initial radius
        # ----------------------------------------------

        initial_radius = self._to_decimal(
            getattr(
                config,
                "initial_search_radius_km",
                None,
            ),
        )

        if initial_radius is None:
            raise DispatchConfigurationError(
                "Initial search radius is not configured."
            )

        if initial_radius <= Decimal("0"):
            raise DispatchConfigurationError(
                "Initial search radius must be "
                "greater than zero."
            )

        # ----------------------------------------------
        # Maximum radius
        # ----------------------------------------------

        maximum_radius = self._to_decimal(
            getattr(
                config,
                "maximum_search_radius_km",
                None,
            ),
        )

        if maximum_radius is None:
            raise DispatchConfigurationError(
                "Maximum search radius is not configured."
            )

        if maximum_radius <= Decimal("0"):
            raise DispatchConfigurationError(
                "Maximum search radius must be "
                "greater than zero."
            )

        # ----------------------------------------------
        # Radius relationship
        # ----------------------------------------------

        if maximum_radius < initial_radius:
            raise DispatchConfigurationError(
                "Maximum search radius must be "
                "greater than or equal to the "
                "initial search radius."
            )

        # ----------------------------------------------
        # Search increment
        # ----------------------------------------------

        increment = self._to_decimal(
            getattr(
                config,
                "search_radius_increment_km",
                None,
            ),
        )

        if increment is None:
            raise DispatchConfigurationError(
                "Search radius increment is not "
                "configured."
            )

        if increment <= Decimal("0"):
            raise DispatchConfigurationError(
                "Search radius increment must be "
                "greater than zero."
            )

        # ----------------------------------------------
        # Rider response timeout
        # ----------------------------------------------

        timeout = self._to_decimal(
            getattr(
                config,
                "rider_response_timeout_seconds",
                None,
            ),
        )

        if timeout is None:
            raise DispatchConfigurationError(
                "Rider response timeout is not configured."
            )

        if timeout <= Decimal("0"):
            raise DispatchConfigurationError(
                "Rider response timeout must be "
                "greater than zero."
            )

        # ----------------------------------------------
        # Normalize timeout to integer seconds
        # ----------------------------------------------

        timeout_seconds = int(
            timeout,
        )

        if timeout_seconds <= 0:
            raise DispatchConfigurationError(
                "Rider response timeout must be "
                "at least one second."
            )

        # ----------------------------------------------
        # Store normalized configuration metadata
        # ----------------------------------------------

        self.context.add_metadata(
            "initial_search_radius_km",
            initial_radius,
        )

        self.context.add_metadata(
            "maximum_search_radius_km",
            maximum_radius,
        )

        self.context.add_metadata(
            "search_radius_increment_km",
            increment,
        )

        self.context.add_metadata(
            "rider_response_timeout_seconds",
            timeout_seconds,
        )

    # ==================================================
    # Failure
    # ==================================================

    def _fail_context(
        self,
        error,
    ):
        """
        Mark the current dispatch context as failed.
        """

        message = str(error)

        self.context.update_status(
            DispatchStatus.FAILED,
        )

        self.context.update_step(
            "Failed",
        )

        self.context.add_error(
            message,
        )

        self.context.add_metadata(
            "dispatch_failed_at",
            timezone.now(),
        )

    # ==================================================
    # Delivery State
    # ==================================================

    def _set_delivery_waiting_for_rider(self):
        """
        Move the delivery into WAITING_FOR_RIDER.

        Allowed starting states:

            PENDING
            WAITING_FOR_RIDER
            FAILED

        Terminal states:

            DELIVERED
            CANCELLED
        """

        delivery = self.context.delivery

        if delivery is None:
            raise NoAvailableRider(
                "Delivery is required for dispatch."
            )

        # ----------------------------------------------
        # Terminal states
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
        # Allowed states
        # ----------------------------------------------

        allowed_statuses = {
            Delivery.DeliveryStatus.PENDING,
            Delivery.DeliveryStatus.WAITING_FOR_RIDER,
            Delivery.DeliveryStatus.FAILED,
        }

        if delivery.status not in allowed_statuses:
            raise NoAvailableRider(
                f"Delivery with status "
                f"'{delivery.status}' cannot "
                f"enter the dispatch workflow."
            )

        # ----------------------------------------------
        # Update state
        # ----------------------------------------------

        now = timezone.now()

        delivery.status = (
            Delivery.DeliveryStatus.WAITING_FOR_RIDER
        )

        update_fields = [
            "status",
        ]

        # ----------------------------------------------
        # waiting_for_rider_at
        # ----------------------------------------------

        if hasattr(
            delivery,
            "waiting_for_rider_at",
        ):

            delivery.waiting_for_rider_at = now

            update_fields.append(
                "waiting_for_rider_at",
            )

        # ----------------------------------------------
        # updated_at
        # ----------------------------------------------

        if hasattr(
            delivery,
            "updated_at",
        ):

            update_fields.append(
                "updated_at",
            )

        delivery.save(
            update_fields=update_fields,
        )

        # ----------------------------------------------
        # Metadata
        # ----------------------------------------------

        self.context.add_metadata(
            "delivery_status",
            delivery.status,
        )

        self.context.add_metadata(
            "waiting_for_rider_at",
            getattr(
                delivery,
                "waiting_for_rider_at",
                now,
            ),
        )

        self.context.update_step(
            "WaitingForRider",
        )

    # ==================================================
    # Find Riders
    # ==================================================

    def _find_matches(self):
        """
        Search progressively larger geographic radii.

        RiderMatcher owns:

            • Geographic search
            • Rider filtering
            • Eligibility query
            • RiderMatch construction

        DispatchPipeline owns only the progressive
        search strategy.
        """

        self.context.update_status(
            DispatchStatus.SEARCHING,
        ).update_step(
            "FindMatches",
        )

        config = self.context.config

        radius = self._to_decimal(
            config.initial_search_radius_km,
        )

        maximum = self._to_decimal(
            config.maximum_search_radius_km,
        )

        increment = self._to_decimal(
            config.search_radius_increment_km,
        )

        if (
            radius is None
            or maximum is None
            or increment is None
        ):
            raise DispatchConfigurationError(
                "Invalid dispatch search configuration."
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

            matches = list(
                matches or [],
            )

            # ------------------------------------------
            # Riders found
            # ------------------------------------------

            if matches:

                self.context.set_matches(
                    matches,
                )

                self.context.search_radius = radius

                self.context.add_metadata(
                    "matched_rider_count",
                    len(matches),
                )

                self.context.add_metadata(
                    "search_radius_km",
                    radius,
                )

                self.context.update_status(
                    DispatchStatus.MATCHED,
                )

                self.context.update_step(
                    "MatchesFound",
                )

                return

            # ------------------------------------------
            # Expand radius
            # ------------------------------------------

            radius += increment

        # ----------------------------------------------
        # No riders
        # ----------------------------------------------

        self.context.add_metadata(
            "matched_rider_count",
            0,
        )

        self.context.add_metadata(
            "search_radius_km",
            maximum,
        )

        raise NoAvailableRider(
            "No eligible rider found within "
            "the configured search radius."
        )

    # ==================================================
    # Rank Riders
    # ==================================================

    def _rank_matches(self):
        """
        Rank RiderMatch objects using RiderRanker.
        """

        self.context.update_step(
            "RankMatches",
        )

        matches = self.context.matches

        if not matches:
            raise NoAvailableRider(
                "No rider matches available "
                "for ranking."
            )

        ranked_matches = RiderRanker.rank(
            context=self.context,
            matches=matches,
        )

        ranked_matches = list(
            ranked_matches or [],
        )

        if not ranked_matches:
            raise NoAvailableRider(
                "Rider ranking returned no "
                "eligible matches."
            )

        self.context.set_ranked_matches(
            ranked_matches,
        )

        self.context.add_metadata(
            "ranked_rider_count",
            len(ranked_matches),
        )

        self.context.update_status(
            DispatchStatus.RANKED,
        )

        self.context.update_step(
            "MatchesRanked",
        )

    # ==================================================
    # Create Offer
    # ==================================================

    def _offer_first_rider(self):
        """
        Create exactly ONE offer for the highest-ranked
        rider who remains eligible.

        A final eligibility check is performed immediately
        before offer creation.

        If offer creation fails because another concurrent
        dispatch process has already created a pending offer
        for the rider, that rider is excluded and the next
        ranked rider is attempted.

        Only one successful offer is created per pipeline run.
        """

        self.context.update_step(
            "CreateOffer",
        )

        ranked_matches = (
            self.context.ranked_matches
        )

        if not ranked_matches:
            raise NoAvailableRider(
                "No ranked rider is available "
                "for dispatch."
            )

        for match in ranked_matches:

            if match is None:
                continue

            rider = getattr(
                match,
                "rider",
                None,
            )

            # ------------------------------------------
            # Invalid match
            # ------------------------------------------

            if rider is None:
                continue

            rider_id = getattr(
                rider,
                "id",
                None,
            )

            if rider_id is None:
                continue

            # ------------------------------------------
            # Existing exclusion
            # ------------------------------------------

            if self.context.is_rider_excluded(
                rider,
            ):
                continue

            # ------------------------------------------
            # Final eligibility check
            # ------------------------------------------

            try:

                eligible = (
                    RiderEligibilityService.is_eligible(
                        rider=rider,
                        context=self.context,
                    )
                )

            except Exception as exc:

                self.context.add_warning(
                    f"Final eligibility validation "
                    f"failed for rider {rider_id}."
                )

                self.context.add_error(
                    str(exc),
                )

                self._exclude_rider(
                    rider_id,
                )

                continue

            if not eligible:

                self.context.add_warning(
                    f"Rider {rider_id} is no longer "
                    "eligible for this dispatch."
                )

                self._exclude_rider(
                    rider_id,
                )

                continue

            # ------------------------------------------
            # Determine offer radius
            # ------------------------------------------

            offer_radius = getattr(
                match,
                "search_radius",
                None,
            )

            if offer_radius is None:
                offer_radius = (
                    self.context.search_radius
                )

            offer_radius = self._to_decimal(
                offer_radius,
            )

            if offer_radius is None:
                raise DispatchConfigurationError(
                    "Unable to determine the search "
                    "radius for the delivery offer."
                )

            if offer_radius <= Decimal("0"):
                raise DispatchConfigurationError(
                    "Delivery offer search radius "
                    "must be greater than zero."
                )

            # ------------------------------------------
            # Timeout
            # ------------------------------------------

            timeout = getattr(
                self.context.config,
                "rider_response_timeout_seconds",
                None,
            )

            timeout = self._to_decimal(
                timeout,
            )

            if timeout is None or timeout <= Decimal("0"):
                raise DispatchConfigurationError(
                    "Invalid rider response timeout."
                )

            timeout_seconds = int(
                timeout,
            )

            if timeout_seconds <= 0:
                raise DispatchConfigurationError(
                    "Rider response timeout must be "
                    "at least one second."
                )

            # ------------------------------------------
            # Create offer
            #
            # IMPORTANT:
            #
            # DeliveryOfferService exposes create(),
            # not create_offer().
            # ------------------------------------------

            try:

                offer = (
                    DeliveryOfferService.create(
                        delivery=self.context.delivery,
                        rider=rider,
                        radius=offer_radius,
                        timeout=timeout_seconds,
                    )
                )

            except InvalidOfferState as exc:

                # --------------------------------------
                # Concurrency / lifecycle conflict
                # --------------------------------------

                self.context.add_warning(
                    f"Unable to create offer for "
                    f"rider {rider_id}: {exc}"
                )

                self._exclude_rider(
                    rider_id,
                )

                continue

            # ------------------------------------------
            # Validate created offer
            # ------------------------------------------

            if offer is None:
                self.context.add_warning(
                    f"Offer creation returned no "
                    f"offer for rider {rider_id}."
                )

                self._exclude_rider(
                    rider_id,
                )

                continue

            # ------------------------------------------
            # Store selection
            # ------------------------------------------

            self.context.select_match(
                match,
            )

            self.context.set_offer(
                offer,
            )

            # ------------------------------------------
            # Metadata
            # ------------------------------------------

            self.context.add_metadata(
                "selected_rider_id",
                rider_id,
            )

            self.context.add_metadata(
                "offer_id",
                offer.id,
            )

            self.context.add_metadata(
                "offer_search_radius_km",
                offer_radius,
            )

            self.context.add_metadata(
                "offer_timeout_seconds",
                timeout_seconds,
            )

            self.context.add_metadata(
                "offer_created_at",
                timezone.now(),
            )

            self.context.add_metadata(
                "offer_created",
                True,
            )

            # ------------------------------------------
            # Notify rider
            # ------------------------------------------

            self._notify_rider(
                offer,
            )

            # ------------------------------------------
            # Final state
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

        Notification failure does NOT invalidate the
        persisted offer.

        The offer remains available for:

            • Rider response
            • Expiration handling
            • Monitoring
            • Recovery
        """

        if offer is None:

            self.context.add_warning(
                "Cannot notify rider because "
                "delivery offer is missing."
            )

            self.context.add_metadata(
                "rider_notified",
                False,
            )

            return False

        try:

            DispatchNotifier.offer_delivery(
                offer,
            )

            self.context.add_metadata(
                "rider_notified",
                True,
            )

            self.context.add_metadata(
                "rider_notified_at",
                timezone.now(),
            )

            return True

        except Exception as exc:

            self.context.add_metadata(
                "rider_notified",
                False,
            )

            # Notification failure is a warning,
            # not a dispatch failure.

            self.context.add_warning(
                "Delivery offer was created, "
                "but rider notification failed."
            )

            self.context.add_warning(
                f"Rider notification error: {exc}"
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

        Persistent offer history remains stored in the
        DeliveryOffer table.

        DispatchCoordinator reconstructs historical
        exclusions for subsequent dispatch attempts.
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
        # Remove from raw matches
        # ----------------------------------------------

        self.context.matches = [
            match
            for match in self.context.matches
            if (
                getattr(
                    match,
                    "rider",
                    None,
                ) is not None
                and getattr(
                    match.rider,
                    "id",
                    None,
                ) != rider_id
            )
        ]

        # ----------------------------------------------
        # Remove from ranked matches
        # ----------------------------------------------

        self.context.ranked_matches = [
            match
            for match in self.context.ranked_matches
            if (
                getattr(
                    match,
                    "rider",
                    None,
                ) is not None
                and getattr(
                    match.rider,
                    "id",
                    None,
                ) != rider_id
            )
        ]

        # ----------------------------------------------
        # Metadata
        # ----------------------------------------------

        self.context.add_metadata(
            "excluded_rider_count",
            len(
                self.context.excluded_rider_ids,
            ),
        )

        self.context.add_metadata(
            "last_excluded_rider_id",
            rider_id,
        )

    # ==================================================
    # Decimal Helper
    # ==================================================

    @staticmethod
    def _to_decimal(
        value,
    ):
        """
        Safely convert configuration/radius values
        to Decimal.

        Returns None when conversion is impossible.
        """

        if value is None:
            return None

        if isinstance(
            value,
            Decimal,
        ):
            return value

        try:

            return Decimal(
                str(value),
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ):

            return None