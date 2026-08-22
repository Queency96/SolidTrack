from decimal import Decimal, InvalidOperation
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
    • Normalize the resulting score
    • Store the score on RiderMatch

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

        Returns
        -------
        RiderMatch
            The same match instance with its score set.
        """

        # ----------------------------------------------
        # Validate context
        # ----------------------------------------------

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        # ----------------------------------------------
        # Validate configuration
        # ----------------------------------------------

        config = context.config

        if config is None:
            raise ValueError(
                "Dispatch configuration is required."
            )

        # ----------------------------------------------
        # Validate match
        # ----------------------------------------------

        if match is None:
            raise ValueError(
                "Rider match is required."
            )

        if match.rider is None:
            raise ValueError(
                "Rider match must contain a rider."
            )

        # ----------------------------------------------
        # Resolve strategy
        # ----------------------------------------------

        strategy_name = getattr(
            config,
            "dispatch_strategy",
            None,
        )

        if not strategy_name:
            raise ValueError(
                "No dispatch strategy configured."
            )

        # ----------------------------------------------
        # Resolve strategy implementation
        # ----------------------------------------------

        strategy = (
            DispatchStrategyFactory.get_strategy(
                strategy_name,
            )
        )

        if strategy is None:
            raise ValueError(
                "No dispatch strategy configured "
                f"for '{strategy_name}'."
            )

        # ----------------------------------------------
        # Calculate score
        # ----------------------------------------------

        score = strategy.score(
            context=context,
            match=match,
        )

        # ----------------------------------------------
        # Validate returned score
        # ----------------------------------------------

        if score is None:
            raise ValueError(
                "Dispatch strategy "
                f"'{strategy_name}' returned no score."
            )

        # ----------------------------------------------
        # Normalize score
        # ----------------------------------------------

        try:
            normalized_score = Decimal(
                str(score)
            )
        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "Dispatch strategy "
                f"'{strategy_name}' returned an "
                f"invalid score: {score!r}."
            ) from exc

        # ----------------------------------------------
        # Validate score
        # ----------------------------------------------

        if normalized_score < 0:
            raise ValueError(
                "Dispatch strategy "
                f"'{strategy_name}' returned a "
                "negative score."
            )

        # ----------------------------------------------
        # Store score
        # ----------------------------------------------

        match.set_score(
            normalized_score,
        )

        return match