from deliveries.models import DispatchConfiguration

from .balanced import (
    BalancedDispatchStrategy,
)
from .nearest import (
    NearestDispatchStrategy,
)
from .performance import (
    PerformanceDispatchStrategy,
)


class DispatchStrategyFactory:
    """
    Resolves the configured dispatch strategy.

    The factory keeps strategy selection centralized so
    the rest of the dispatch system does not need to know
    which concrete strategy is being used.
    """

    # ==================================================
    # Strategy Registry
    # ==================================================

    STRATEGIES = {
        DispatchConfiguration.DispatchStrategy.BALANCED:
            BalancedDispatchStrategy(),

        DispatchConfiguration.DispatchStrategy.NEAREST:
            NearestDispatchStrategy(),

        DispatchConfiguration.DispatchStrategy.PERFORMANCE:
            PerformanceDispatchStrategy(),
    }

    # ==================================================
    # Get Strategy
    # ==================================================

    @classmethod
    def get_strategy(
        cls,
        strategy,
    ):
        """
        Return the configured dispatch strategy.

        Raises:
            ValueError:
                If the configured strategy is not registered.
        """

        if not strategy:
            raise ValueError(
                "A dispatch strategy must be configured."
            )

        try:
            return cls.STRATEGIES[strategy]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported dispatch strategy: "
                f"'{strategy}'."
            ) from exc