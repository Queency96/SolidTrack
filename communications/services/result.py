from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CommunicationResult:
    """
    Standard result returned by every
    communication channel.
    """

    success: bool
    message: str
    provider: str
    response: Any = None

    @classmethod
    def success_result(
        cls,
        provider,
        response=None,
        message="Success",
    ):
        return cls(
            success=True,
            provider=provider,
            message=message,
            response=response,
        )

    @classmethod
    def failure_result(
        cls,
        provider,
        message,
        response=None,
    ):
        return cls(
            success=False,
            provider=provider,
            message=message,
            response=response,
        )