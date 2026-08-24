from .coordinator import DispatchCoordinator
from .result import DispatchResult


class DispatchEngine:
    """
    Public entry point for the delivery dispatch system.

    DispatchEngine is intentionally thin.

    It acts as the public facade for dispatch operations
    and delegates the actual dispatch lifecycle to
    DispatchCoordinator.

    It does not:
        • Find riders
        • Check rider eligibility
        • Calculate distances
        • Score riders
        • Create offers
        • Assign riders
        • Manage rider responses
        • Manage redispatch
        • Manage dispatch attempts

    Those responsibilities belong to the dispatch
    subsystem components.

    Architecture
    ------------

        DispatchEngine
              ↓
        DispatchCoordinator
              ↓
        DispatchConfigurationService
              ↓
        DispatchContext
              ↓
        DispatchPipeline
              ↓
        RiderEligibilityService
              ↓
        RiderMatcher
              ↓
        RiderScorer
              ↓
        DeliveryOfferService
              ↓
        DispatchNotifier
              ↓
        Rider response
              ↓
        DispatchCoordinator
              ↓
        AssignmentService

    DispatchEngine therefore provides a stable public API
    without duplicating dispatch lifecycle logic.
    """

    # ==================================================
    # Dispatch
    # ==================================================

    @classmethod
    def dispatch(
        cls,
        delivery,
        excluded_rider_ids=None,
        attempt=None,
    ) -> DispatchResult:
        """
        Start the dispatch lifecycle for a delivery.

        Parameters
        ----------
        delivery : Delivery
            Delivery that requires rider dispatch.

        excluded_rider_ids : iterable, optional
            Rider IDs that must not receive an offer during
            this dispatch invocation.

            Persistent exclusions are automatically loaded
            by DispatchCoordinator.

        attempt : int, optional
            Explicit dispatch attempt number.

            If omitted, DispatchCoordinator determines the
            current attempt from persistent DeliveryOffer
            history.

        Returns
        -------
        DispatchResult
            Standardized dispatch result.

        Raises
        ------
        ValueError
            If delivery is not provided.

        Notes
        -----
        DispatchEngine intentionally delegates all lifecycle
        management to DispatchCoordinator.

        This prevents duplicate implementations of:

            • configuration loading
            • context creation
            • persistent rider exclusions
            • attempt tracking
            • terminal delivery validation
            • failure handling
            • redispatch behavior
        """

        # ----------------------------------------------
        # Validate delivery
        # ----------------------------------------------

        if delivery is None:
            raise ValueError(
                "Delivery is required for dispatch."
            )

        # ----------------------------------------------
        # Delegate to coordinator
        # ----------------------------------------------

        return DispatchCoordinator.dispatch(
            delivery=delivery,
            excluded_rider_ids=excluded_rider_ids,
            attempt=attempt,
        )

    # ==================================================
    # Delivery Created
    # ==================================================

    @classmethod
    def delivery_created(
        cls,
        delivery,
    ) -> DispatchResult:
        """
        Start dispatch after a delivery has been created.

        This method should be used when the application
        wants the complete delivery-created workflow,
        including publication of the DeliveryCreatedEvent.

        The actual dispatch lifecycle remains owned by
        DispatchCoordinator.
        """

        if delivery is None:
            raise ValueError(
                "Delivery is required."
            )

        return DispatchCoordinator.delivery_created(
            delivery=delivery,
        )

    # ==================================================
    # Offer Response
    # ==================================================

    @classmethod
    def respond_to_offer(
        cls,
        offer,
        action,
        reason="",
    ) -> DispatchResult:
        """
        Process a rider's response to a delivery offer.

        Parameters
        ----------
        offer : DeliveryOffer
            The delivery offer being responded to.

        action : DeliveryOfferAction
            ACCEPT or REJECT.

        reason : str, optional
            Rejection reason when the rider rejects
            the offer.

        Returns
        -------
        DispatchResult
            Result of the rider response.

        Notes
        -----
        Offer response handling belongs to
        DispatchCoordinator.

        DispatchEngine simply exposes it as part of the
        public dispatch API.
        """

        if offer is None:
            raise ValueError(
                "Delivery offer is required."
            )

        return DispatchCoordinator.respond_to_offer(
            offer=offer,
            action=action,
            reason=reason,
        )

    # ==================================================
    # Offer Expiration
    # ==================================================

    @classmethod
    def offer_expired(
        cls,
        offer,
    ) -> DispatchResult:
        """
        Handle an expired delivery offer.

        DispatchCoordinator determines whether automatic
        redispatch is enabled and starts the next dispatch
        attempt when appropriate.
        """

        if offer is None:
            raise ValueError(
                "Delivery offer is required."
            )

        return DispatchCoordinator.offer_expired(
            offer=offer,
        )

    # ==================================================
    # Cancel Offer
    # ==================================================

    @classmethod
    def cancel_offer(
        cls,
        offer,
    ) -> DispatchResult:
        """
        Cancel a pending delivery offer.

        Cancellation does not automatically redispatch
        the delivery.
        """

        if offer is None:
            raise ValueError(
                "Delivery offer is required."
            )

        return DispatchCoordinator.cancel_offer(
            offer=offer,
        )
