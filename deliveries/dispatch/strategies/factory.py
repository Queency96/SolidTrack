from deliveries.models import DispatchConfiguration

from .balanced import BalancedDispatchStrategy
from .customer_priority import CustomerPriorityDispatchStrategy
from .express import ExpressDispatchStrategy
from .fair_distribution import FairDistributionDispatchStrategy
from .nearest import NearestDispatchStrategy
from .performance import PerformanceDispatchStrategy
from .vendor_priority import VendorPriorityDispatchStrategy


class DispatchStrategyFactory:
    """
    Resolves the configured dispatch strategy.

    The factory keeps strategy selection centralized so
    the rest of the dispatch system does not need to know
    which concrete strategy is being used.

    Supported strategies
    --------------------
    • BALANCED
    • NEAREST
    • PERFORMANCE
    • VENDOR_PRIORITY
    • CUSTOMER_PRIORITY
    • FAIR_DISTRIBUTION
    • EXPRESS
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
        Return an instantiated dispatch strategy.

        Parameters
        ----------
        strategy : str
            DispatchConfiguration.DispatchStrategy value.

        Returns
        -------
        BaseDispatchStrategy
            Instantiated strategy.

        Raises
        ------
        ValueError
            If no strategy was supplied or the strategy
            is not registered.
        """

        # ----------------------------------------------
        # Validate strategy
        # ----------------------------------------------

        if not strategy:
            raise ValueError(
                "A dispatch strategy must be configured."
            )

        # ----------------------------------------------
        # Resolve strategy class
        # ----------------------------------------------

        strategy_class = cls.STRATEGIES.get(
            strategy,
        )

        if strategy_class is None:
            raise ValueError(
                "Unsupported dispatch strategy: "
                f"'{strategy}'."
            )

        # ----------------------------------------------
        # Instantiate
        # ----------------------------------------------

        return strategy_class()

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
            cls.STRATEGIES.keys()
        )