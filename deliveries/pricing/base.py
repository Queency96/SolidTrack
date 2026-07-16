from abc import ABC
from abc import abstractmethod


class PricingStrategy(ABC):

    @abstractmethod
    def calculate(self, *args, **kwargs):
        pass