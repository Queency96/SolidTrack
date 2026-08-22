from abc import ABC, abstractmethod
from decimal import Decimal

from ..context import DispatchContext
from ..match import RiderMatch


class BaseDispatchStrategy(ABC):
    """
    Base interface for all dispatch strategies.

    Every dispatch strategy must calculate a score for
    a RiderMatch.

    Higher scores indicate better rider matches.

    Strategies should operate on the normalized
    RiderMatch interface rather than accessing Django
    models directly.
    """

    # ==================================================
    # Score
    # ==================================================

    @abstractmethod
    def score(
        self,
        context: DispatchContext,
        match: RiderMatch,
    ) -> Decimal:
        """
        Calculate the dispatch score for a rider match.

        Parameters
        ----------
        context : DispatchContext
            Current dispatch context containing the
            delivery and dispatch configuration.

        match : RiderMatch
            Dispatch-layer representation of the rider.

            RiderMatch provides normalized access to:

            • Rider
            • Distance
            • Search radius
            • Active delivery count
            • Rating
            • Acceptance rate
            • Completion rate
            • Cancellation rate
            • Completed deliveries
            • Metadata

        Returns
        -------
        Decimal
            Dispatch score for the rider.

        Notes
        -----
        Higher scores indicate better rider matches.
        """

        raise NotImplementedError