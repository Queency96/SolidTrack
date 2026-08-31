from dataclasses import dataclass, field
from typing import Any
from deliveries.models.delivery import Delivery
from deliveries.models.delivery_assignment import DeliveryAssignment
from deliveries.models.delivery_offer import DeliveryOffer
from .context import DispatchContext
from .status import DispatchStatus


@dataclass(slots=True)
class DispatchResult:
    """
    Standard result returned by the dispatch subsystem.

    DispatchResult only represents the outcome.

    It does NOT:

        • modify database state
        • create offers
        • create assignments
        • send notifications
        • perform dispatch logic
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

    # ==================================================
    # Factories
    # ==================================================

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
            message=str(message),
            **kwargs,
        )

    @classmethod
    def failure_result(
        cls,
        status=DispatchStatus.FAILED,
        message="Dispatch failed.",
        **kwargs,
    ):
        return cls(
            success=False,
            status=status,
            message=str(message),
            **kwargs,
        )

    @classmethod
    def failure(
        cls,
        message,
        status=DispatchStatus.FAILED,
        **kwargs,
    ):
        return cls.failure_result(
            status=status,
            message=message,
            **kwargs,
        )

    # ==================================================
    # Convenience
    # ==================================================

    @property
    def is_success(self):
        return self.success

    @property
    def is_failure(self):
        return not self.success

    @property
    def has_errors(self):
        return bool(self.errors)

    @property
    def has_warnings(self):
        return bool(self.warnings)

    @property
    def has_delivery(self):
        return self.delivery is not None

    @property
    def has_offer(self):
        return self.offer is not None

    @property
    def has_assignment(self):
        return self.assignment is not None

    # ==================================================
    # Warning
    # ==================================================

    def add_warning(
        self,
        message,
    ):
        if message is None:
            return self

        message = str(message)

        if message not in self.warnings:
            self.warnings.append(message)

        return self

    # ==================================================
    # Error
    # ==================================================

    def add_error(
        self,
        message,
    ):
        if message is None:
            return self

        message = str(message)

        if message not in self.errors:
            self.errors.append(message)

        self.success = False
        self.status = DispatchStatus.FAILED

        return self

    # ==================================================
    # Data
    # ==================================================

    def add_data(
        self,
        key,
        value,
    ):
        self.data[key] = value
        return self

    def get_data(
        self,
        key,
        default=None,
    ):
        return self.data.get(
            key,
            default,
        )

    # ==================================================
    # Merge
    # ==================================================

    def merge(
        self,
        other,
    ):
        if other is None:
            return self

        if not isinstance(
            other,
            DispatchResult,
        ):
            raise TypeError(
                "Can only merge another "
                "DispatchResult."
            )

        if not other.success:
            self.success = False
            self.status = other.status

        for error in other.errors:
            if error not in self.errors:
                self.errors.append(error)

        for warning in other.warnings:
            if warning not in self.warnings:
                self.warnings.append(warning)

        self.data.update(
            other.data,
        )

        if self.context is None:
            self.context = other.context

        if self.delivery is None:
            self.delivery = other.delivery

        if self.offer is None:
            self.offer = other.offer

        if self.assignment is None:
            self.assignment = other.assignment

        return self

    # ==================================================
    # Context Synchronization
    # ==================================================

    def sync_context(self):
        if self.context is None:
            return self

        context = self.context

        if self.delivery is None:
            self.delivery = context.delivery

        if self.offer is None:
            self.offer = context.offer

        if self.assignment is None:
            self.assignment = context.assignment

        for warning in context.warnings:
            if warning not in self.warnings:
                self.warnings.append(warning)

        for error in context.errors:
            if error not in self.errors:
                self.errors.append(error)

        if self.errors:
            self.success = False
            self.status = DispatchStatus.FAILED

        return self

    # ==================================================
    # Previous Offer
    # ==================================================

    @property
    def previous_offer_id(self):
        return self.get_data(
            "previous_offer_id",
        )

    @property
    def previous_offer_status(self):
        return self.get_data(
            "previous_offer_status",
        )

    # ==================================================
    # Current Rider
    # ==================================================

    @property
    def selected_rider(self):
        if self.context is None:
            return None

        return self.context.selected_rider

    # ==================================================
    # Search
    # ==================================================

    @property
    def search_radius(self):
        if self.context is None:
            return None

        return self.context.search_radius

    @property
    def match_count(self):
        if self.context is None:
            return 0

        return len(
            self.context.matches,
        )

    @property
    def ranked_match_count(self):
        if self.context is None:
            return 0

        return len(
            self.context.ranked_matches,
        )

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(self):
        status = self.status

        if hasattr(status, "value"):
            status = status.value

        payload = {
            "success": self.success,
            "status": str(status),
            "message": self.message,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "data": dict(self.data),
        }

        if self.delivery is not None:
            payload["delivery_id"] = self.delivery.id

        if self.offer is not None:
            payload["offer_id"] = self.offer.id

        if self.assignment is not None:
            payload["assignment_id"] = self.assignment.id

        rider = self.selected_rider

        if rider is not None:
            payload["rider_id"] = rider.id

        if self.previous_offer_id is not None:
            payload["previous_offer_id"] = (
                self.previous_offer_id
            )

        if self.previous_offer_status is not None:
            payload["previous_offer_status"] = (
                self.previous_offer_status
            )

        if self.context is not None:

            context_status = self.context.status

            if hasattr(
                context_status,
                "value",
            ):
                context_status = context_status.value

            payload["dispatch"] = {
                "status": str(context_status),
                "current_step": (
                    self.context.current_step
                ),
                "attempt": (
                    self.context.attempt
                ),
                "search_radius": (
                    str(
                        self.context.search_radius
                    )
                    if self.context.search_radius
                    is not None
                    else None
                ),
                "match_count": len(
                    self.context.matches
                ),
                "ranked_match_count": len(
                    self.context.ranked_matches
                ),
                "excluded_rider_count": (
                    self.context.excluded_rider_count
                ),
            }

        return payload

    # ==================================================
    # Boolean
    # ==================================================

    def __bool__(self):
        return self.success