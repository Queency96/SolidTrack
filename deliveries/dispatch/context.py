from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from .match import RiderMatch
from accounts.models import User
from deliveries.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
    DispatchConfiguration,
)
from vendors.models import VendorProfile

from .status import DispatchStatus


@dataclass(slots=True)
class DispatchContext:
    """
    Shared state for the complete dispatch workflow.

    Every dispatch component receives the same context
    instance and updates it throughout the lifecycle.
    """

    # --------------------------------------------------
    # Core
    # --------------------------------------------------

    delivery: Delivery

    config: DispatchConfiguration

    status: DispatchStatus = (
        DispatchStatus.CREATED
    )

    current_step: str = "INITIALIZED"

    attempt: int = 1

    # --------------------------------------------------
    # Relationships
    # --------------------------------------------------

    customer: User | None = None

    vendor: VendorProfile | None = None

    selected_rider: User | None = None

    # --------------------------------------------------
    # Search
    # --------------------------------------------------

    search_radius: Decimal = Decimal("0")

    matches: list[RiderMatch] = field(
        default_factory=list,
    )

    ranked_matches: list[RiderMatch] = field(
        default_factory=list,
    )

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    offer: DeliveryOffer | None = None

    assignment: DeliveryAssignment | None = None

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    warnings: list[str] = field(
        default_factory=list,
    )

    errors: list[str] = field(
        default_factory=list,
    )

    # --------------------------------------------------
    # Initialization
    # --------------------------------------------------

    def __post_init__(self):
        """
        Populate related objects automatically.
        """

        if self.customer is None:
            self.customer = self.delivery.customer

        if (
            self.vendor is None
            and hasattr(self.delivery, "vendor")
        ):
            self.vendor = self.delivery.vendor

    # --------------------------------------------------
    # State
    # --------------------------------------------------

    def update_status(
        self,
        status: DispatchStatus,
    ):
        self.status = status
        return self

    def update_step(
        self,
        step: str,
    ):
        self.current_step = step
        return self

    def increment_attempt(
        self,
    ):
        self.attempt += 1
        return self

    # --------------------------------------------------
    # Metadata
    # --------------------------------------------------

    def add_metadata(
        self,
        key,
        value,
    ):
        self.metadata[key] = value
        return self

    def add_warning(
        self,
        message,
    ):
        self.warnings.append(message)
        return self

    def add_error(
        self,
        message,
    ):
        self.errors.append(message)
        return self

    # --------------------------------------------------
    # Bulk Update
    # --------------------------------------------------

    def set(
        self,
        **kwargs,
    ):
        for key, value in kwargs.items():
            setattr(self, key, value)
        return self

    # --------------------------------------------------
    # Convenience Properties
    # --------------------------------------------------

    @property
    def has_matches(
        self,
    ):
        return bool(self.matches)

    @property
    def has_assignment(
        self,
    ):
        return self.assignment is not None

    @property
    def has_offer(
        self,
    ):
        return self.offer is not None

    @property
    def has_errors(
        self,
    ):
        return bool(self.errors)