from dataclasses import dataclass, field
from typing import Any

from deliveries.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
)

from .context import DispatchContext
from .status import DispatchStatus


@dataclass(slots=True)
class DispatchResult:
    """
    Standard result returned by the dispatch subsystem.

    Every public dispatch operation returns this object.
    """

    success: bool

    status: DispatchStatus

    message: str

    context: DispatchContext | None = None

    delivery: Delivery | None = None

    assignment: DeliveryAssignment | None = None

    offer: DeliveryOffer | None = None

    data: dict[str, Any] = field(
        default_factory=dict,
    )

    warnings: list[str] = field(
        default_factory=list,
    )

    errors: list[str] = field(
        default_factory=list,
    )

    # --------------------------------------------------
    # Factory Methods
    # --------------------------------------------------

    @classmethod
    def success_result(
        cls,
        status,
        message,
        **kwargs,
    ):
        return cls(
            success=True,
            status=status,
            message=message,
            **kwargs,
        )

    @classmethod
    def failure(
        cls,
        message,
        status=DispatchStatus.FAILED,
        **kwargs,
    ):
        return cls(
            success=False,
            status=status,
            message=message,
            **kwargs,
        )

    # --------------------------------------------------
    # Convenience Properties
    # --------------------------------------------------

    @property
    def has_errors(self):

        return bool(self.errors)

    @property
    def has_warnings(self):

        return bool(self.warnings)

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    def add_warning(
        self,
        message,
    ):

        self.warnings.append(
            message,
        )

        return self

    def add_error(
        self,
        message,
    ):

        self.errors.append(
            message,
        )

        self.success = False

        return self

    def merge(
        self,
        other,
    ):
        """
        Merge another DispatchResult into this one.
        Useful when composing multiple services.
        """

        self.errors.extend(
            other.errors,
        )

        self.warnings.extend(
            other.warnings,
        )

        self.data.update(
            other.data,
        )

        if not other.success:
            self.success = False

        return self

    # --------------------------------------------------
    # Serialization
    # --------------------------------------------------

    def to_dict(
        self,
    ):

        payload = {
            "success": self.success,
            "status": self.status,
            "message": self.message,
            "errors": self.errors,
            "warnings": self.warnings,
            "data": self.data,
        }

        if self.delivery:
            payload["delivery_id"] = (
                self.delivery.id
            )

        if self.assignment:
            payload["assignment_id"] = (
                self.assignment.id
            )

        if self.offer:
            payload["offer_id"] = (
                self.offer.id
            )

        return payload