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

        Any supplied warnings or errors are preserved.
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

        This is the canonical failure factory used by
        DispatchEngine, DispatchPipeline, and
        DispatchCoordinator.
        """

        return cls(
            success=False,
            status=status,
            message=str(message),
            **kwargs,
        )

    # ==================================================
    # Backward-Compatible Failure Alias
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
    def has_errors(
        self,
    ):
        """
        Return True when the result contains errors.
        """

        return bool(
            self.errors,
        )

    @property
    def has_warnings(
        self,
    ):
        """
        Return True when the result contains warnings.
        """

        return bool(
            self.warnings,
        )

    @property
    def has_delivery(
        self,
    ):
        """
        Return True when a delivery is attached.
        """

        return (
            self.delivery
            is not None
        )

    @property
    def has_offer(
        self,
    ):
        """
        Return True when an offer is attached.
        """

        return (
            self.offer
            is not None
        )

    @property
    def has_assignment(
        self,
    ):
        """
        Return True when an assignment is attached.
        """

        return (
            self.assignment
            is not None
        )

    @property
    def is_success(
        self,
    ):
        """
        Alias for success.
        """

        return self.success

    @property
    def is_failure(
        self,
    ):
        """
        Return True when the operation failed.
        """

        return not self.success

    # ==================================================
    # Warning Helpers
    # ==================================================

    def add_warning(
        self,
        message,
    ):
        """
        Add a non-fatal warning.

        Warnings do not change the success state.
        """

        self.warnings.append(
            str(message),
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

        self.errors.append(
            str(message),
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
        Add a value to the result data payload.
        """

        self.data[key] = value

        return self

    def get_data(
        self,
        key,
        default=None,
    ):
        """
        Safely retrieve a value from result data.
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

        Errors, warnings, and arbitrary data are merged.

        A failed result always causes the resulting
        result to become unsuccessful.
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
        # Errors
        # ----------------------------------------------

        self.errors.extend(
            other.errors,
        )

        # ----------------------------------------------
        # Warnings
        # ----------------------------------------------

        self.warnings.extend(
            other.warnings,
        )

        # ----------------------------------------------
        # Data
        # ----------------------------------------------

        self.data.update(
            other.data,
        )

        # ----------------------------------------------
        # Success state
        # ----------------------------------------------

        if not other.success:
            self.success = False

        # ----------------------------------------------
        # Preserve useful objects
        # ----------------------------------------------

        if (
            self.context is None
            and other.context is not None
        ):
            self.context = other.context

        if (
            self.delivery is None
            and other.delivery is not None
        ):
            self.delivery = other.delivery

        if (
            self.offer is None
            and other.offer is not None
        ):
            self.offer = other.offer

        if (
            self.assignment is None
            and other.assignment is not None
        ):
            self.assignment = (
                other.assignment
            )

        return self

    # ==================================================
    # Context Synchronization
    # ==================================================

    def sync_context(
        self,
    ):
        """
        Synchronize result information from the current
        DispatchContext.

        This is useful when the pipeline has accumulated
        warnings/errors after an intermediate result was
        created.
        """

        if self.context is None:
            return self

        # ----------------------------------------------
        # Objects
        # ----------------------------------------------

        if self.delivery is None:
            self.delivery = (
                self.context.delivery
            )

        if self.offer is None:
            self.offer = (
                self.context.offer
            )

        if self.assignment is None:
            self.assignment = (
                self.context.assignment
            )

        # ----------------------------------------------
        # Warnings
        # ----------------------------------------------

        for warning in self.context.warnings:

            if warning not in self.warnings:
                self.warnings.append(
                    warning,
                )

        # ----------------------------------------------
        # Errors
        # ----------------------------------------------

        for error in self.context.errors:

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
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ):
        """
        Convert the result into a JSON-friendly
        dictionary.

        Django model objects themselves are never returned
        directly.
        """

        payload = {
            "success": self.success,
            "status": (
                self.status.value
                if hasattr(
                    self.status,
                    "value",
                )
                else str(self.status)
            ),
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
        # Dispatch context
        # ----------------------------------------------

        if self.context is not None:

            payload["dispatch"] = {
                "status": (
                    self.context.status.value
                    if hasattr(
                        self.context.status,
                        "value",
                    )
                    else str(
                        self.context.status
                    )
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
                ),
                "match_count": len(
                    self.context.matches
                ),
                "ranked_match_count": len(
                    self.context.ranked_matches
                ),
                "excluded_rider_count": (
                    self.context
                    .excluded_rider_count
                ),
            }

        return payload

    # ==================================================
    # Representation
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