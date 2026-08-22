from decimal import Decimal

from .context import DispatchContext
from .match import RiderMatch
from .strategies.factory import DispatchStrategyFactory


class RiderScorer:
    """
    Calculates the dispatch score for a rider.

    The actual scoring algorithm is delegated to the
    configured dispatch strategy.

    Responsibilities
    ----------------
    • Resolve the configured dispatch strategy
    • Execute the strategy
    • Store the resulting score on RiderMatch

    This class does NOT:
    • Find riders
    • Check rider eligibility
    • Calculate distance
    • Create offers
    • Assign riders
    • Notify riders/customers/vendors
    """

    # ==================================================
    # Score Rider
    # ==================================================

    @classmethod
    def score(
        cls,
        context: DispatchContext,
        match: RiderMatch,
    ) -> RiderMatch:
        """
        Calculate and store the dispatch score
        for a rider match.
        """

        # ------------------------------------------
        # Validate context
        # ------------------------------------------

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        # ------------------------------------------
        # Validate match
        # ------------------------------------------

        if match is None:
            raise ValueError(
                "Rider match is required."
            )

        if match.rider is None:
            raise ValueError(
                "Rider match must contain a rider."
            )

        # ------------------------------------------
        # Resolve configured strategy
        # ------------------------------------------

        strategy_name = getattr(
            context.config,
            "dispatch_strategy",
            None,
        )

        if not strategy_name:
            raise ValueError(
                "No dispatch strategy configured."
            )

        strategy = (
            DispatchStrategyFactory.get_strategy(
                strategy_name,
            )
        )

        if strategy is None:
            raise ValueError(
                f"No dispatch strategy configured "
                f"for '{strategy_name}'."
            )

        # ------------------------------------------
        # Calculate score
        # ------------------------------------------

        score = strategy.score(
            context=context,
            match=match,
        )

        # ------------------------------------------
        # Normalize score
        # ------------------------------------------

        if score is None:
            raise ValueError(
                f"Dispatch strategy "
                f"'{strategy_name}' returned no score."
            )

        score = Decimal(
            str(score)
        )

        # ------------------------------------------
        # Store score
        # ------------------------------------------

        match.set_score(
            score,
        )

        return match