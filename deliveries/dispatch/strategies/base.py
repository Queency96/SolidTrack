from abc import ABC, abstractmethod


class BaseDispatchStrategy(ABC):

    @abstractmethod
    def score(
        self,
        context,
        match,
    ):
        pass