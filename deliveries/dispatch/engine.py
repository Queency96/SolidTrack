from .pipeline import DispatchPipeline


class DispatchEngine:
    @classmethod
    def dispatch(cls, delivery):
        """
        Entry point for dispatching a delivery.
        """
        return DispatchPipeline(
            delivery
        ).run()