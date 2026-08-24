from decimal import Decimal

from .base import BaseDispatchStrategy


class NearestDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Nearest-rider dispatch strategy.

    Prioritizes riders according to their distance
    from the pickup location.

    The closer the rider is to the pickup location,
    the higher the resulting score.

    This strategy intentionally ignores:

        • Rider rating
        • Acceptance rate
        • Completion rate
        • Cancellation rate
        • Experience
        • Workload

    Rider eligibility has already been handled by
    RiderEligibilityService.
    """

    # ==================================================
    # Configuration
    # ==================================================

    BASE_SCORE = Decimal("100000.00")

    # ==================================================
    # Scoring
    # ==================================================

    def score(
        self,
        context,
        match,
    ) -> Decimal:
        """
        Calculate the proximity score.

        A smaller distance produces a higher score.

        Example
        -------
        Rider A: 2 km
            100000 - 2 = 99998

        Rider B: 5 km
            100000 - 5 = 99995

        Therefore Rider A ranks above Rider B.
        """

        # ----------------------------------------------
        # Validate inputs
        # ----------------------------------------------

        self.validate_inputs(
            context=context,
            match=match,
        )

        # ----------------------------------------------
        # Get distance
        # ----------------------------------------------

        distance = self.non_negative_decimal(
            match.distance,
        )

        # ----------------------------------------------
        # Calculate score
        # ----------------------------------------------

        score = (
            self.BASE_SCORE
            - distance
        )

        # ----------------------------------------------
        # Prevent negative scores
        # ----------------------------------------------

        return max(
            score,
            Decimal("0"),
        )