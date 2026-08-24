from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation

from ..context import DispatchContext
from ..match import RiderMatch


class BaseDispatchStrategy(ABC):
    """
    Base interface for all dispatch strategies.

    Every concrete dispatch strategy must calculate a
    dispatch score for a RiderMatch.

    Higher scores indicate better rider matches.

    Responsibilities
    ----------------
    • Define the strategy scoring contract
    • Validate common strategy inputs
    • Provide Decimal conversion helpers

    This class does NOT:
        • Find riders
        • Check rider eligibility
        • Calculate geographic distance
        • Rank riders
        • Create offers
        • Assign riders
        • Notify riders

    Score normalization is handled by RiderScorer.
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
            Current dispatch context.

        match : RiderMatch
            RiderMatch being evaluated.

        Returns
        -------
        Decimal
            Calculated dispatch score.

        Notes
        -----
        Higher scores indicate better rider matches.

        Concrete strategies should return Decimal.
        """

        raise NotImplementedError(
            "Dispatch strategies must implement "
            "the score() method."
        )

    # ==================================================
    # Validation
    # ==================================================

    @classmethod
    def validate_inputs(
        cls,
        context: DispatchContext,
        match: RiderMatch,
    ):
        """
        Validate the common inputs required by every
        dispatch strategy.

        Concrete strategies should normally call:

            self.validate_inputs(
                context=context,
                match=match,
            )
        """

        # ----------------------------------------------
        # Context
        # ----------------------------------------------

        if context is None:
            raise ValueError(
                "Dispatch context is required."
            )

        # ----------------------------------------------
        # Configuration
        # ----------------------------------------------

        if context.config is None:
            raise ValueError(
                "Dispatch configuration is required."
            )

        # ----------------------------------------------
        # Delivery
        # ----------------------------------------------

        if context.delivery is None:
            raise ValueError(
                "Dispatch context must contain "
                "a delivery."
            )

        # ----------------------------------------------
        # Match
        # ----------------------------------------------

        if match is None:
            raise ValueError(
                "Rider match is required."
            )

        # ----------------------------------------------
        # Rider
        # ----------------------------------------------

        if match.rider is None:
            raise ValueError(
                "Rider match must contain a rider."
            )

        return True

    # ==================================================
    # Decimal Conversion
    # ==================================================

    @staticmethod
    def decimal(
        value,
        default=Decimal("0"),
    ) -> Decimal:
        """
        Safely convert a value to Decimal.

        This helper prevents accidental float arithmetic
        inside dispatch scoring calculations.

        Invalid values return the supplied default.
        """

        if value is None:
            return default

        if isinstance(
            value,
            Decimal,
        ):
            return value

        try:

            return Decimal(
                str(value),
            )

        except (
            TypeError,
            ValueError,
            InvalidOperation,
        ):
            return default

    # ==================================================
    # Non-Negative Decimal
    # ==================================================

    @classmethod
    def non_negative_decimal(
        cls,
        value,
        default=Decimal("0"),
    ) -> Decimal:
        """
        Convert a value to Decimal and prevent negative
        values.

        Useful for scoring components such as:

            • distance
            • performance
            • priority
            • workload
            • rating
        """

        value = cls.decimal(
            value,
            default=default,
        )

        return max(
            value,
            Decimal("0"),
        )