from decimal import Decimal, InvalidOperation

from django.db import IntegrityError
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

    The pipeline is responsible only for orchestrating the
    search-and-offer phase of dispatch.

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

    Rider responses are handled asynchronously by
    DispatchCoordinator.

    Responsibilities
    ----------------
    DispatchPipeline DOES:

        • Coordinate the dispatch search workflow.
        • Perform progressive-radius searching.
        • Coordinate rider matching.
        • Coordinate rider ranking.
        • Perform final eligibility validation.
        • Create one DeliveryOffer.
        • Notify the selected rider.
        • Maintain transient DispatchContext state.

    DispatchPipeline DOES NOT:

        • Accept offers.
        • Reject offers.
        • Expire offers.
        • Cancel offers.
        • Create DeliveryAssignment records.
        • Accept assignments.
        • Complete assignments.
        • Manage rider availability.
        • Calculate rider scores.
        • Implement geographic matching logic.
        • Implement ranking logic.
        • Orchestrate redispatch.
        • Persist dispatch history.

    Those responsibilities belong to the appropriate services
    and DispatchCoordinator.

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
        RiderRanker
                ↓
        RiderEligibilityService
                ↓
        DeliveryOfferService
                ↓
        DispatchNotifier

    Assignment lifecycle is deliberately outside this class.
    """

    # ==================================================
    # Initialization
    # ==================================================

    def __init__(self, context: DispatchContext):
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
            # Begin dispatch
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
            # Create exactly one offer
            # ------------------------------------------

            self._offer_first_rider()

            # ------------------------------------------
            # Successful dispatch
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

            self._fail_context(exc)

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=str(exc),
                context=self.context,
                delivery=self.context.delivery,
                offer=self.context.offer,
                errors=[str(exc)],
            )

        except Exception as exc:

            self._fail_context(exc)

            return DispatchResult.failure_result(
                status=DispatchStatus.FAILED,
                message=(
                    "An unexpected error occurred "
                    "during dispatch."
                ),
                context=self.context,
                delivery=self.context.delivery,
                offer=self.context.offer,
                errors=[str(exc)],
            )

    # ==================================================
    # Attempt Preparation
    # ==================================================

    def _prepare_attempt(self):
        """
        Prepare the context for the current dispatch attempt.

        DispatchContext represents the current in-memory
        attempt.

        Persistent dispatch history remains in the database.

        IMPORTANT
        ---------
        Persistent exclusions supplied by DispatchCoordinator
        are not cleared here.
        """

        attempt = self.context.attempt

        if attempt is None or attempt < 1:
            attempt = 1

        self.context.attempt = attempt

        # ----------------------------------------------
        # Clear transient selection state
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
            attempt,
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

        self.context.add_metadata(
            "selected_rider_id",
            None,
        )

        self.context.add_metadata(
            "offer_id",
            None,
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

        if getattr(
            self.context.delivery,
            "pk",
            None,
        ) is None:
            raise DispatchConfigurationError(
                "Delivery must be persisted before dispatch."
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
            )
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
            )
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
            )
        )

        if increment is None:
            raise DispatchConfigurationError(
                "Search radius increment is not configured."
            )

        if increment <= Decimal("0"):
            raise DispatchConfigurationError(
                "Search radius increment must be "
                "greater than zero."
            )

        # ----------------------------------------------
        # Response timeout
        # ----------------------------------------------

        timeout = self._to_decimal(
            getattr(
                config,
                "rider_response_timeout_seconds",
                None,
            )
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
        # Timeout must represent whole seconds
        # ----------------------------------------------

        if timeout != timeout.to_integral_value():
            raise DispatchConfigurationError(
                "Rider response timeout must be "
                "a whole number of seconds."
            )

        timeout_seconds = int(timeout)

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

    def _fail_context(self, error):
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
            raise DispatchConfigurationError(
                "Delivery is required for dispatch."
            )

        status = delivery.status

        # ----------------------------------------------
        # Terminal states
        # ----------------------------------------------

        if status == Delivery.DeliveryStatus.DELIVERED:
            raise DispatchConfigurationError(
                "Cannot dispatch an already delivered delivery."
            )

        if status == Delivery.DeliveryStatus.CANCELLED:
            raise DispatchConfigurationError(
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

        if status not in allowed_statuses:
            raise DispatchConfigurationError(
                f"Delivery with status '{status}' "
                "cannot enter the dispatch workflow."
            )

        # ----------------------------------------------
        # Update state
        # ----------------------------------------------

        now = timezone.now()

        delivery.status = (
            Delivery.DeliveryStatus.WAITING_FOR_RIDER
        )

        update_fields = ["status"]

        if hasattr(
            delivery,
            "waiting_for_rider_at",
        ):
            delivery.waiting_for_rider_at = now
            update_fields.append(
                "waiting_for_rider_at"
            )

        if hasattr(
            delivery,
            "updated_at",
        ):
            update_fields.append("updated_at")

        delivery.save(
            update_fields=update_fields,
        )

        # ----------------------------------------------
        # Context metadata
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

        RiderMatcher owns geographic searching and rider
        matching.

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
            getattr(
                config,
                "initial_search_radius_km",
                None,
            )
        )

        maximum = self._to_decimal(
            getattr(
                config,
                "maximum_search_radius_km",
                None,
            )
        )

        increment = self._to_decimal(
            getattr(
                config,
                "search_radius_increment_km",
                None,
            )
        )

        if (
            radius is None
            or maximum is None
            or increment is None
        ):
            raise DispatchConfigurationError(
                "Invalid dispatch search configuration."
            )

        searched_radii = []

        # ----------------------------------------------
        # Progressive search
        # ----------------------------------------------

        while radius <= maximum:

            searched_radii.append(radius)

            self.context.update_step(
                f"FindMatches:{radius}km",
            )

            matches = RiderMatcher.find_nearby_riders(
                context=self.context,
                radius_km=radius,
            )

            matches = list(matches or [])

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

                self.context.add_metadata(
                    "searched_radii_km",
                    searched_radii,
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

            next_radius = radius + increment

            if next_radius <= radius:
                raise DispatchConfigurationError(
                    "Search radius increment did not "
                    "increase the search radius."
                )

            radius = next_radius

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

        self.context.add_metadata(
            "searched_radii_km",
            searched_radii,
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

        matches = list(
            self.context.matches or []
        )

        # ----------------------------------------------
        # Remove already excluded riders
        # ----------------------------------------------

        matches = [
            match
            for match in matches
            if (
                match is not None
                and getattr(match, "rider", None) is not None
                and not self.context.is_rider_excluded(
                    match.rider
                )
            )
        ]

        if not matches:
            raise NoAvailableRider(
                "No rider matches available for ranking."
            )

        ranked_matches = RiderRanker.rank(
            context=self.context,
            matches=matches,
        )

        ranked_matches = list(
            ranked_matches or []
        )

        # ----------------------------------------------
        # Remove excluded riders returned by ranker
        # ----------------------------------------------

        ranked_matches = [
            match
            for match in ranked_matches
            if (
                match is not None
                and getattr(match, "rider", None) is not None
                and not self.context.is_rider_excluded(
                    match.rider
                )
            )
        ]

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
        eligible rider.

        A final eligibility check occurs immediately before
        offer creation.

        If another concurrent dispatch process has already
        created an offer for the rider, the rider is excluded
        from the current attempt and the next ranked rider
        is tried.

        This method NEVER creates a DeliveryAssignment.
        """

        self.context.update_step(
            "CreateOffer",
        )

        ranked_matches = list(
            self.context.ranked_matches or []
        )

        if not ranked_matches:
            raise NoAvailableRider(
                "No ranked rider is available for dispatch."
            )

        for match in ranked_matches:

            if match is None:
                continue

            rider = getattr(
                match,
                "rider",
                None,
            )

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
            # Final eligibility validation
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
                    "Final eligibility validation "
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
                offer_radius = self.context.search_radius

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

            timeout_seconds = self._get_timeout_seconds()

            # ------------------------------------------
            # Create offer
            # ------------------------------------------

            try:
                offer = DeliveryOfferService.create(
                    delivery=self.context.delivery,
                    rider=rider,
                    radius=offer_radius,
                    timeout=timeout_seconds,
                )

            except InvalidOfferState as exc:

                self.context.add_warning(
                    f"Unable to create offer for "
                    f"rider {rider_id}: {exc}"
                )

                self._exclude_rider(
                    rider_id,
                )

                continue

            except IntegrityError as exc:

                """
                A database constraint may still reject the
                operation when two dispatch processes race.

                This is treated as a rider-level concurrency
                conflict rather than a complete dispatch failure.
                """

                self.context.add_warning(
                    f"Concurrent offer creation conflict "
                    f"for rider {rider_id}."
                )

                self.context.add_error(
                    str(exc),
                )

                self._exclude_rider(
                    rider_id,
                )

                continue

            # ------------------------------------------
            # Validate result
            # ------------------------------------------

            if offer is None:
                self.context.add_warning(
                    f"Offer creation returned no offer "
                    f"for rider {rider_id}."
                )

                self._exclude_rider(
                    rider_id,
                )

                continue

            # ------------------------------------------
            # Store selected match
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
            )

            self.context.update_step(
                "OfferCreated",
            )

            return

        # ----------------------------------------------
        # No eligible rider remains
        # ----------------------------------------------

        raise NoAvailableRider(
            "No eligible rider remains for dispatch."
        )

    # ==================================================
    # Timeout
    # ==================================================

    def _get_timeout_seconds(self):
        """
        Return the normalized rider response timeout.

        Configuration was already validated by
        _validate_configuration(), but this method keeps
        offer creation defensive.
        """

        timeout = self._to_decimal(
            getattr(
                self.context.config,
                "rider_response_timeout_seconds",
                None,
            )
        )

        if timeout is None:
            raise DispatchConfigurationError(
                "Invalid rider response timeout."
            )

        if timeout <= Decimal("0"):
            raise DispatchConfigurationError(
                "Rider response timeout must be "
                "greater than zero."
            )

        if timeout != timeout.to_integral_value():
            raise DispatchConfigurationError(
                "Rider response timeout must be "
                "a whole number of seconds."
            )

        timeout_seconds = int(timeout)

        if timeout_seconds <= 0:
            raise DispatchConfigurationError(
                "Rider response timeout must be "
                "at least one second."
            )

        return timeout_seconds

    # ==================================================
    # Notification
    # ==================================================

    def _notify_rider(self, offer):
        """
        Notify the selected rider.

        Notification failure does NOT invalidate the
        persisted DeliveryOffer.

        The offer remains available for:

            • Rider response
            • Expiration
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

    def _exclude_rider(self, rider_id):
        """
        Exclude a rider from the current dispatch context.

        This is transient state.

        Persistent offer history remains stored in
        DeliveryOffer and is reconstructed by
        DispatchCoordinator for later attempts.
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
            for match in (
                self.context.matches or []
            )
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
            for match in (
                self.context.ranked_matches or []
            )
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

        excluded_ids = getattr(
            self.context,
            "excluded_rider_ids",
            set(),
        )

        self.context.add_metadata(
            "excluded_rider_count",
            len(excluded_ids),
        )

        self.context.add_metadata(
            "last_excluded_rider_id",
            rider_id,
        )

    # ==================================================
    # Decimal Helper
    # ==================================================

    @staticmethod
    def _to_decimal(value):
        """
        Safely convert configuration/radius values
        to Decimal.

        Returns None when conversion is impossible.
        """

        if value is None:
            return None

        if isinstance(value, Decimal):
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