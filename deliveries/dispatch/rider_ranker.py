
from .scorer import RiderScorer


class RiderRanker:
    """
    Ranks matched riders according to the configured
    dispatch strategy.

    Responsibilities
    ----------------
    • Receive RiderMatch objects
    • Score each rider through RiderScorer
    • Sort riders by score
    • Preserve distance as a secondary ordering factor
    • Store ranking metadata

    The ranker does NOT:
    • Find riders
    • Check rider eligibility
    • Calculate distance
    • Create offers
    • Assign riders
    • Notify riders
    """

    # ==================================================
    # Rank Matches
    # ==================================================

    @classmethod
    def rank(
        cls,
        context,
        matches=None,
    ):
        """
        Score and rank rider matches.

        Parameters
        ----------
        context : DispatchContext
            Current dispatch context.

        matches : list[RiderMatch] | None
            Matches to rank.

            If omitted, context.matches is used.

        Returns
        -------
        list[RiderMatch]
            Riders ordered from highest score
            to lowest score.
        """

        # ----------------------------------------------
        # Validate context
        # ----------------------------------------------

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        # ----------------------------------------------
        # Resolve matches
        # ----------------------------------------------

        if matches is None:
            matches = context.matches

        if not matches:
            context.ranked_matches = []

            return []

        # ----------------------------------------------
        # Score matches
        # ----------------------------------------------

        ranked_matches = []

        for match in matches:

            if match is None:
                continue

            scored_match = RiderScorer.score(
                context=context,
                match=match,
            )

            ranked_matches.append(
                scored_match,
            )

        # ----------------------------------------------
        # Sort by score
        # ----------------------------------------------
        #
        # Primary:
        #   Higher score first
        #
        # Secondary:
        #   Shorter distance first
        #
        # This means that if two riders have the
        # same score, the closer rider wins.

        ranked_matches.sort(
            key=lambda match: (
                -match.score,
                match.distance_km,
            ),
        )

        # ----------------------------------------------
        # Store ranking position
        # ----------------------------------------------

        for index, match in enumerate(
            ranked_matches,
            start=1,
        ):
            match.add_metadata(
                "rank",
                index,
            )

        # ----------------------------------------------
        # Update context
        # ----------------------------------------------

        context.ranked_matches = (
            ranked_matches
        )

        return ranked_matches

    # ==================================================
    # Best Match
    # ==================================================

    @classmethod
    def best_match(
        cls,
        context,
        matches=None,
    ):
        """
        Return the highest-ranked rider match.

        If matches have not already been ranked,
        they are ranked first.
        """

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        if matches is None:
            matches = context.ranked_matches

        if not matches:
            matches = cls.rank(
                context=context,
                matches=context.matches,
            )

        if not matches:
            return None

        return matches[0]

    # ==================================================
    # Top Matches
    # ==================================================

    @classmethod
    def top_matches(
        cls,
        context,
        limit=5,
    ):
        """
        Return the top N ranked rider matches.
        """

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        try:
            limit = int(limit)
        except (
            TypeError,
            ValueError,
        ):
            limit = 5

        if limit <= 0:
            return []

        if not context.ranked_matches:
            cls.rank(
                context=context,
                matches=context.matches,
            )

        return context.ranked_matches[
            :limit
        ]

    # ==================================================
    # Re-rank
    # ==================================================

    @classmethod
    def rerank(
        cls,
        context,
    ):
        """
        Re-score and re-rank the current matches.

        Useful when rider metrics or dispatch metadata
        have changed during the dispatch lifecycle.
        """

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        return cls.rank(
            context=context,
            matches=context.matches,
        )