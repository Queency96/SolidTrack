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

    Strategies operate on the normalized RiderMatch
    interface and should not access Django models
    directly for dispatch calculations.
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
            Normalized dispatch-layer representation
            of the rider.

        Returns
        -------
        Decimal
            Dispatch score.

        Raises
        ------
        ValueError
            If the context or match is invalid.

        Notes
        -----
        Higher scores indicate better rider matches.

        Concrete strategies should return a Decimal.
        """

        raise NotImplementedError(
            "Dispatch strategies must implement "
            "the score() method."
        )

    # ==================================================
    # Validation
    # ==================================================

    @staticmethod
    def validate_inputs(
        context: DispatchContext,
        match: RiderMatch,
    ):
        """
        Validate common strategy inputs.

        Concrete strategies can call this method before
        performing their scoring calculations.
        """

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        if context.config is None:
            raise ValueError(
                "Dispatch configuration is required."
            )

        if match is None:
            raise ValueError(
                "Rider match is required."
            )

        if match.rider is None:
            raise ValueError(
                "Rider match must contain a rider."
            )

    # ==================================================
    # Decimal Helper
    # ==================================================

    @staticmethod
    def decimal(
        value,
        default=Decimal("0"),
    ) -> Decimal:
        """
        Safely convert a numeric value to Decimal.

        This helper keeps scoring calculations
        deterministic and avoids float arithmetic.
        """

        if value is None:
            return default

        return Decimal(
            str(value)
        )