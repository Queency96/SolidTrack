from decimal import Decimal, InvalidOperation
from .context import DispatchContext
from .match import RiderMatch
from .strategies.factory import DispatchStrategyFactory


class RiderScorer:
    """
    Calculates the dispatch score for a rider match.

    Responsibilities
    ----------------
    • Validate the dispatch context
    • Validate the rider match
    • Resolve the configured dispatch strategy
    • Execute the strategy
    • Normalize the returned score
    • Store the raw score
    • Store the normalized score on RiderMatch
    • Store scoring metadata

    This class does NOT:
        • Find riders
        • Check rider eligibility
        • Calculate geographic distance
        • Rank riders
        • Create offers
        • Assign riders
        • Notify users
    """

    # ==================================================
    # Score
    # ==================================================

    @classmethod
    def score(
        cls,
        context: DispatchContext,
        match: RiderMatch,
    ) -> RiderMatch:
        """
        Calculate and store the dispatch score.

        Parameters
        ----------
        context : DispatchContext
            Current dispatch context.

        match : RiderMatch
            Rider match being scored.

        Returns
        -------
        RiderMatch
            The same match with its score populated.

        Raises
        ------
        ValueError
            If the context, configuration, match,
            strategy, or calculated score is invalid.
        """

        # ----------------------------------------------
        # Validate context
        # ----------------------------------------------

        cls._validate_context(
            context,
        )

        # ----------------------------------------------
        # Validate match
        # ----------------------------------------------

        cls._validate_match(
            match,
        )

        # ----------------------------------------------
        # Resolve strategy
        # ----------------------------------------------

        strategy_name = (
            context.config.dispatch_strategy
        )

        if not strategy_name:
            raise ValueError(
                "Dispatch strategy is required."
            )

        try:

            strategy = (
                DispatchStrategyFactory.get_strategy(
                    strategy_name,
                )
            )

        except Exception as exc:

            raise ValueError(
                "Unable to resolve dispatch strategy "
                f"'{strategy_name}'."
            ) from exc

        if strategy is None:
            raise ValueError(
                "Dispatch strategy "
                f"'{strategy_name}' could not be resolved."
            )

        # ----------------------------------------------
        # Calculate raw score
        # ----------------------------------------------

        raw_score = strategy.score(
            context=context,
            match=match,
        )

        # ----------------------------------------------
        # Normalize score
        # ----------------------------------------------

        normalized_score = (
            cls._normalize_score(
                score=raw_score,
                strategy_name=strategy_name,
            )
        )

        # ----------------------------------------------
        # Store scoring metadata
        # ----------------------------------------------

        match.add_metadata(
            "dispatch_strategy",
            strategy_name,
        )

        match.add_metadata(
            "raw_score",
            normalized_score,
        )

        # ----------------------------------------------
        # Store final score
        # ----------------------------------------------

        match.set_score(
            normalized_score,
        )

        return match

    # ==================================================
    # Validate Context
    # ==================================================

    @staticmethod
    def _validate_context(
        context: DispatchContext,
    ):
        """
        Validate the dispatch context required
        for scoring.
        """

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        if context.config is None:
            raise ValueError(
                "Dispatch configuration is required."
            )

        if context.delivery is None:
            raise ValueError(
                "Dispatch context must contain "
                "a delivery."
            )

    # ==================================================
    # Validate Match
    # ==================================================

    @staticmethod
    def _validate_match(
        match: RiderMatch,
    ):
        """
        Validate the RiderMatch before scoring.
        """

        if match is None:
            raise ValueError(
                "Rider match is required."
            )

        if match.rider is None:
            raise ValueError(
                "Rider match must contain a rider."
            )

    # ==================================================
    # Normalize Score
    # ==================================================

    @staticmethod
    def _normalize_score(
        score,
        strategy_name,
    ) -> Decimal:
        """
        Normalize a strategy score to Decimal.

        Rules
        -----
        • None is invalid.
        • Invalid numeric values are rejected.
        • Negative scores become zero.
        • Positive infinity is rejected.
        • Negative infinity is rejected.
        """

        if score is None:
            raise ValueError(
                "Dispatch strategy "
                f"'{strategy_name}' returned no score."
            )

        try:

            normalized = Decimal(
                str(score),
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError,
        ) as exc:

            raise ValueError(
                "Dispatch strategy "
                f"'{strategy_name}' returned "
                f"an invalid score: {score!r}."
            ) from exc

        # ----------------------------------------------
        # Reject non-finite values
        # ----------------------------------------------

        if not normalized.is_finite():
            raise ValueError(
                "Dispatch strategy "
                f"'{strategy_name}' returned "
                f"a non-finite score: {score!r}."
            )

        # ----------------------------------------------
        # Prevent negative dispatch scores
        # ----------------------------------------------

        return max(
            normalized,
            Decimal("0"),
        )