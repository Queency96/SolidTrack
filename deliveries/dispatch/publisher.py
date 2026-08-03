from collections import defaultdict


class EventPublisher:

    _listeners = defaultdict(list)

    @classmethod
    def subscribe(
        cls,
        event,
        listener,
    ):
        cls._listeners[event].append(
            listener
        )

    @classmethod
    def publish(
        cls,
        event,
    ):

        for listener in cls._listeners[
            type(event)
        ]:
            listener(event)