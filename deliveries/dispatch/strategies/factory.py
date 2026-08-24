from deliveries.models import DispatchConfiguration
from .balanced import BalancedDispatchStrategy
from .customer_priority import (
    CustomerPriorityDispatchStrategy,
)
from .express import ExpressDispatchStrategy
from .fair_distribution import (
    FairDistributionDispatchStrategy,
)
from .nearest import NearestDispatchStrategy
from .performance import PerformanceDispatchStrategy
from .vendor_priority import (
    VendorPriorityDispatchStrategy,
)


class DispatchStrategyFactory:
    """
    Resolves the configured dispatch strategy.

    The factory is responsible only for translating a
    DispatchConfiguration strategy value into the
    corresponding strategy implementation.

    Responsibilities
    ----------------
    • Maintain the strategy registry
    • Resolve a strategy
    • Instantiate the strategy
    • Validate whether a strategy is supported
    • Expose registered strategy values

    The factory does NOT:
        • Find riders
        • Check rider eligibility
        • Calculate distance
        • Calculate scores
        • Rank riders
        • Create offers
        • Assign riders
        • Notify riders
    """

    # ==================================================
    # Strategy Registry
    # ==================================================

    STRATEGIES = {
        DispatchConfiguration.DispatchStrategy.BALANCED:
            BalancedDispatchStrategy,

        DispatchConfiguration.DispatchStrategy.NEAREST:
            NearestDispatchStrategy,

        DispatchConfiguration.DispatchStrategy.PERFORMANCE:
            PerformanceDispatchStrategy,

        DispatchConfiguration.DispatchStrategy.VENDOR_PRIORITY:
            VendorPriorityDispatchStrategy,

        DispatchConfiguration.DispatchStrategy.CUSTOMER_PRIORITY:
            CustomerPriorityDispatchStrategy,

        DispatchConfiguration.DispatchStrategy.FAIR_DISTRIBUTION:
            FairDistributionDispatchStrategy,

        DispatchConfiguration.DispatchStrategy.EXPRESS:
            ExpressDispatchStrategy,
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
        Resolve and instantiate a dispatch strategy.

        Parameters
        ----------
        strategy : str
            Configured dispatch strategy value.

        Returns
        -------
        BaseDispatchStrategy
            Instantiated strategy.

        Raises
        ------
        ValueError
            If the strategy is missing or unsupported.
        """

        if not strategy:
            raise ValueError(
                "A dispatch strategy must be configured."
            )

        strategy = str(strategy).strip()

        strategy_class = cls.STRATEGIES.get(
            strategy,
        )

        if strategy_class is None:
            raise ValueError(
                "Unsupported dispatch strategy: "
                f"'{strategy}'."
            )

        return strategy_class()

    # ==================================================
    # Get Strategy Class
    # ==================================================

    @classmethod
    def get_strategy_class(
        cls,
        strategy,
    ):
        """
        Return the registered strategy class without
        instantiating it.

        Useful for testing, introspection, and dependency
        validation.
        """

        if not strategy:
            raise ValueError(
                "A dispatch strategy must be configured."
            )

        strategy = str(strategy).strip()

        strategy_class = cls.STRATEGIES.get(
            strategy,
        )

        if strategy_class is None:
            raise ValueError(
                "Unsupported dispatch strategy: "
                f"'{strategy}'."
            )

        return strategy_class

    # ==================================================
    # Check Strategy
    # ==================================================

    @classmethod
    def is_supported(
        cls,
        strategy,
    ) -> bool:
        """
        Determine whether a dispatch strategy is
        registered.
        """

        if not strategy:
            return False

        strategy = str(strategy).strip()

        return strategy in cls.STRATEGIES

    # ==================================================
    # Available Strategies
    # ==================================================

    @classmethod
    def available_strategies(
        cls,
    ):
        """
        Return all registered dispatch strategy values.
        """

        return tuple(
            cls.STRATEGIES.keys(),
        )

    # ==================================================
    # Available Strategy Classes
    # ==================================================

    @classmethod
    def available_strategy_classes(
        cls,
    ):
        """
        Return the registered strategy classes.
        """

        return tuple(
            cls.STRATEGIES.values(),
        )