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

    STRATEGIES = {

        DispatchConfiguration.DispatchStrategy.BALANCED:
            BalancedDispatchStrategy(),

        DispatchConfiguration.DispatchStrategy.NEAREST:
            NearestDispatchStrategy(),

        DispatchConfiguration.DispatchStrategy.PERFORMANCE:
            PerformanceDispatchStrategy(),
    }

    @classmethod
    def get_strategy(
        cls,
        strategy,
    ):
        return cls.STRATEGIES.get(
            strategy,
            BalancedDispatchStrategy(),
        )