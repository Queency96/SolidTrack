from .context import DispatchContext
from .match import RiderMatch
from .strategies.factory import DispatchStrategyFactory


class RiderScorer:
    """
    Calculates the dispatch score for a rider.

    The actual scoring algorithm is delegated to the
    configured dispatch strategy.
    """

    @classmethod
    def score(
        cls,
        context: DispatchContext,
        match: RiderMatch,
    ):

        strategy = (
            DispatchStrategyFactory.get_strategy(
                context.config.dispatch_strategy
            )
        )

        score = strategy.score(
            context=context,
            match=match,
        )

        match.set_score(score)

        return score