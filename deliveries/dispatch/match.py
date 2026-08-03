from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from accounts.models import User


@dataclass(slots=True)
class RiderMatch:
    """
    Represents a rider matched to a delivery.
    """

    rider: User
    distance: Decimal
    search_radius: Decimal
    score: Decimal = Decimal("0.00")
    metadata: dict[str, Any] = field(
        default_factory=dict,
    )
    @property
    def location(self):
        return getattr(
            self.rider,
            "location",
            None,
        )
    def set_score(
        self,
        score,
    ):
        self.score = Decimal(
            str(score)
        )
        return self
    def add_metadata(
        self,
        key,
        value,
    ):
        self.metadata[key] = value
        return self