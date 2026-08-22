from decimal import Decimal

from .base import BaseDispatchStrategy


class NearestDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Nearest-rider dispatch strategy.

    Prioritizes riders primarily according to their
    distance from the pickup location.

    The closer the rider is to the pickup location,
    the higher the resulting score.

    This strategy intentionally ignores:
        • Rider rating
        • Acceptance rate
        • Completion rate
        • Cancellation rate
        • Experience
        • Workload

    Eligibility has already been handled by
    RiderEligibilityService.
    """

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
        Calculate the rider's proximity score.

        A smaller distance produces a higher score.
        """

        distance = Decimal(
            str(match.distance_km)
        )

        return (
            self.BASE_SCORE
            - distance
        )