from .context import DispatchContext
from .pipeline import DispatchPipeline
from .service import DispatchConfigurationService


class DispatchEngine:
    """
    Public entry point for the delivery dispatch system.

    DispatchEngine is intentionally thin.

    It does not:
        • Find riders
        • Check rider eligibility
        • Calculate distances
        • Score riders
        • Create offers
        • Assign riders

    Those responsibilities belong to DispatchPipeline
    and its supporting services.

    Flow
    ----
    DispatchEngine
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
    RiderMatch
        ↓
    RiderScorer
        ↓
    DeliveryOfferService
        ↓
    Rider acceptance
        ↓
    AssignmentService
    """

    # ==================================================
    # Dispatch
    # ==================================================

    @classmethod
    def dispatch(
        cls,
        delivery,
    ):
        """
        Start the dispatch lifecycle for a delivery.

        Parameters
        ----------
        delivery : Delivery
            Delivery that needs a rider.

        Returns
        -------
        DispatchResult
            Result returned by DispatchPipeline.

        Raises
        ------
        ValueError
            If delivery is not provided.

        DispatchConfigurationError
            If no valid active dispatch configuration
            exists.

        DispatchException
            Dispatch-specific exceptions raised by the
            underlying dispatch pipeline.
        """

        # ----------------------------------------------
        # Validate delivery
        # ----------------------------------------------

        if delivery is None:
            raise ValueError(
                "Delivery is required for dispatch."
            )

        # ----------------------------------------------
        # Load dispatch configuration
        # ----------------------------------------------

        config = (
            DispatchConfigurationService
            .get_configuration()
        )

        # ----------------------------------------------
        # Create dispatch context
        # ----------------------------------------------

        context = DispatchContext(
            delivery=delivery,
            config=config,
        )

        # ----------------------------------------------
        # Create dispatch pipeline
        # ----------------------------------------------

        pipeline = DispatchPipeline(
            context=context,
        )

        # ----------------------------------------------
        # Execute dispatch
        # ----------------------------------------------

        return pipeline.run()