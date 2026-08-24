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

    Every public dispatch operation should return this
    object.

    DispatchResult is responsible only for representing
    the outcome of a dispatch operation.

    It does NOT:
        • Modify database state
        • Perform dispatch logic
        • Create offers
        • Assign riders
        • Send notifications
    """

    # ==================================================
    # Core Result
    # ==================================================

    success: bool

    status: DispatchStatus

    message: str

    # ==================================================
    # Dispatch Objects
    # ==================================================

    context: DispatchContext | None = None

    delivery: Delivery | None = None

    assignment: DeliveryAssignment | None = None

    offer: DeliveryOffer | None = None

    # ==================================================
    # Additional Data
    # ==================================================

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
    # Success Factory
    # ==================================================

    @classmethod
    def success_result(
        cls,
        status,
        message,
        **kwargs,
    ):
        """
        Create a successful DispatchResult.
        """

        return cls(
            success=True,
            status=status,
            message=str(message),
            **kwargs,
        )

    # ==================================================
    # Failure Factory
    # ==================================================

    @classmethod
    def failure_result(
        cls,
        status=DispatchStatus.FAILED,
        message="Dispatch failed.",
        **kwargs,
    ):
        """
        Create a failed DispatchResult.
        """

        return cls(
            success=False,
            status=status,
            message=str(message),
            **kwargs,
        )

    # ==================================================
    # Backward Compatibility
    # ==================================================

    @classmethod
    def failure(
        cls,
        message,
        status=DispatchStatus.FAILED,
        **kwargs,
    ):
        """
        Backward-compatible alias for failure_result().
        """

        return cls.failure_result(
            status=status,
            message=message,
            **kwargs,
        )

    # ==================================================
    # Convenience Properties
    # ==================================================

    @property
    def is_success(self):
        """
        Return True when the dispatch operation succeeded.
        """

        return self.success

    @property
    def is_failure(self):
        """
        Return True when the dispatch operation failed.
        """

        return not self.success

    @property
    def has_errors(self):
        """
        Return True when errors exist.
        """

        return bool(self.errors)

    @property
    def has_warnings(self):
        """
        Return True when warnings exist.
        """

        return bool(self.warnings)

    @property
    def has_delivery(self):
        """
        Return True when a delivery is attached.
        """

        return self.delivery is not None

    @property
    def has_offer(self):
        """
        Return True when an offer is attached.
        """

        return self.offer is not None

    @property
    def has_assignment(self):
        """
        Return True when an assignment is attached.
        """

        return self.assignment is not None

    # ==================================================
    # Warning Helpers
    # ==================================================

    def add_warning(
        self,
        message,
    ):
        """
        Add a non-fatal warning.

        Warnings do not automatically mark the result
        as failed.
        """

        if message is None:
            return self

        message = str(message)

        if message not in self.warnings:
            self.warnings.append(
                message,
            )

        return self

    # ==================================================
    # Error Helpers
    # ==================================================

    def add_error(
        self,
        message,
    ):
        """
        Add an error and mark the result as failed.
        """

        if message is None:
            return self

        message = str(message)

        if message not in self.errors:
            self.errors.append(
                message,
            )

        self.success = False

        return self

    # ==================================================
    # Data Helpers
    # ==================================================

    def add_data(
        self,
        key,
        value,
    ):
        """
        Add arbitrary data to the result.
        """

        self.data[key] = value

        return self

    def get_data(
        self,
        key,
        default=None,
    ):
        """
        Safely retrieve data from the result.
        """

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
        """
        Merge another DispatchResult into this result.

        The current result remains the primary result.

        Missing objects are populated from the other
        result.

        Errors and warnings are combined without
        unnecessary duplicates.
        """

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

        # ----------------------------------------------
        # Success state
        # ----------------------------------------------

        if not other.success:
            self.success = False

        # ----------------------------------------------
        # Errors
        # ----------------------------------------------

        for error in other.errors:

            if error not in self.errors:
                self.errors.append(
                    error,
                )

        # ----------------------------------------------
        # Warnings
        # ----------------------------------------------

        for warning in other.warnings:

            if warning not in self.warnings:
                self.warnings.append(
                    warning,
                )

        # ----------------------------------------------
        # Data
        # ----------------------------------------------

        self.data.update(
            other.data,
        )

        # ----------------------------------------------
        # Context
        # ----------------------------------------------

        if (
            self.context is None
            and other.context is not None
        ):
            self.context = other.context

        # ----------------------------------------------
        # Delivery
        # ----------------------------------------------

        if (
            self.delivery is None
            and other.delivery is not None
        ):
            self.delivery = other.delivery

        # ----------------------------------------------
        # Offer
        # ----------------------------------------------

        if (
            self.offer is None
            and other.offer is not None
        ):
            self.offer = other.offer

        # ----------------------------------------------
        # Assignment
        # ----------------------------------------------

        if (
            self.assignment is None
            and other.assignment is not None
        ):
            self.assignment = other.assignment

        return self

    # ==================================================
    # Context Synchronization
    # ==================================================

    def sync_context(
        self,
    ):
        """
        Synchronize the result with its DispatchContext.

        This is particularly useful after the pipeline
        has accumulated warnings or errors.
        """

        if self.context is None:
            return self

        context = self.context

        # ----------------------------------------------
        # Delivery
        # ----------------------------------------------

        if self.delivery is None:
            self.delivery = context.delivery

        # ----------------------------------------------
        # Offer
        # ----------------------------------------------

        if self.offer is None:
            self.offer = context.offer

        # ----------------------------------------------
        # Assignment
        # ----------------------------------------------

        if self.assignment is None:
            self.assignment = context.assignment

        # ----------------------------------------------
        # Warnings
        # ----------------------------------------------

        for warning in context.warnings:

            if warning not in self.warnings:
                self.warnings.append(
                    warning,
                )

        # ----------------------------------------------
        # Errors
        # ----------------------------------------------

        for error in context.errors:

            if error not in self.errors:
                self.errors.append(
                    error,
                )

        # ----------------------------------------------
        # Failure state
        # ----------------------------------------------

        if self.errors:
            self.success = False

        return self

    # ==================================================
    # Previous Offer Helpers
    # ==================================================

    @property
    def previous_offer_id(self):
        """
        Return the ID of the previous offer when the
        redispatch flow recorded one.
        """

        return self.get_data(
            "previous_offer_id",
        )

    @property
    def previous_offer_status(self):
        """
        Return the status of the previous offer when
        recorded during redispatch.
        """

        return self.get_data(
            "previous_offer_status",
        )

    # ==================================================
    # Current Rider
    # ==================================================

    @property
    def selected_rider(self):
        """
        Return the rider selected for the current
        dispatch offer.
        """

        if self.context is None:
            return None

        return self.context.selected_rider

    # ==================================================
    # Search Information
    # ==================================================

    @property
    def search_radius(self):
        """
        Return the search radius used by the current
        dispatch attempt.
        """

        if self.context is None:
            return None

        return self.context.search_radius

    @property
    def match_count(self):
        """
        Return the number of current rider matches.
        """

        if self.context is None:
            return 0

        return len(
            self.context.matches,
        )

    @property
    def ranked_match_count(self):
        """
        Return the number of ranked rider matches.
        """

        if self.context is None:
            return 0

        return len(
            self.context.ranked_matches,
        )

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ):
        """
        Convert the result into a JSON-friendly
        dictionary.

        Django model instances are represented by IDs.
        """

        status = self.status

        if hasattr(
            status,
            "value",
        ):
            status = status.value

        payload = {
            "success": self.success,
            "status": str(status),
            "message": self.message,
            "errors": list(
                self.errors,
            ),
            "warnings": list(
                self.warnings,
            ),
            "data": dict(
                self.data,
            ),
        }

        # ----------------------------------------------
        # Delivery
        # ----------------------------------------------

        if self.delivery is not None:

            payload["delivery_id"] = (
                self.delivery.id
            )

        # ----------------------------------------------
        # Offer
        # ----------------------------------------------

        if self.offer is not None:

            payload["offer_id"] = (
                self.offer.id
            )

        # ----------------------------------------------
        # Assignment
        # ----------------------------------------------

        if self.assignment is not None:

            payload["assignment_id"] = (
                self.assignment.id
            )

        # ----------------------------------------------
        # Selected rider
        # ----------------------------------------------

        rider = self.selected_rider

        if rider is not None:

            payload["rider_id"] = rider.id

        # ----------------------------------------------
        # Previous offer
        # ----------------------------------------------

        previous_offer_id = (
            self.previous_offer_id
        )

        if previous_offer_id is not None:

            payload["previous_offer_id"] = (
                previous_offer_id
            )

        previous_offer_status = (
            self.previous_offer_status
        )

        if previous_offer_status is not None:

            payload["previous_offer_status"] = (
                previous_offer_status
            )

        # ----------------------------------------------
        # Dispatch context
        # ----------------------------------------------

        if self.context is not None:

            context_status = (
                self.context.status
            )

            if hasattr(
                context_status,
                "value",
            ):
                context_status = (
                    context_status.value
                )

            payload["dispatch"] = {
                "status": str(
                    context_status,
                ),
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
                "match_count": (
                    len(
                        self.context.matches,
                    )
                ),
                "ranked_match_count": (
                    len(
                        self.context.ranked_matches,
                    )
                ),
                "excluded_rider_count": (
                    self.context
                    .excluded_rider_count
                ),
            }

        return payload

    # ==================================================
    # Boolean Representation
    # ==================================================

    def __bool__(
        self,
    ):
        """
        Allow:

            if result:
                ...

        to represent result.success.
        """

        return self.success