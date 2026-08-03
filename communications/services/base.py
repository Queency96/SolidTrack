from abc import ABC, abstractmethod


class BaseCommunicationService(ABC):
    """
    Base class for every communication channel.
    """

    @classmethod
    @abstractmethod
    def send(cls, *args, **kwargs):
        raise NotImplementedError