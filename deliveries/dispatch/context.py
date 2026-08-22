from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from accounts.models import User
from deliveries.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
    DispatchConfiguration,
)
from vendors.models import VendorProfile

from .match import RiderMatch
from .status import DispatchStatus


@dataclass(slots=True)
class DispatchContext:
    """
    Shared state for the complete dispatch workflow.

    Every dispatch component receives the same context
    instance and updates it throughout the lifecycle.

    Persistent dispatch history remains stored in:
        • DeliveryOffer
        • DeliveryAssignment
        • Delivery
        • Related dispatch models

    This context represents the in-memory state of one
    dispatch attempt.
    """

    # ==================================================
    # Core
    # ==================================================

    delivery: Delivery

    config: DispatchConfiguration

    status: DispatchStatus = (
        DispatchStatus.CREATED
    )

    current_step: str = "INITIALIZED"

    attempt: int = 1

    # ==================================================
    # Relationships
    # ==================================================

    customer: User | None = None

    vendor: VendorProfile | None = None

    selected_rider: User | None = None

    selected_match: RiderMatch | None = None

    # ==================================================
    # Search
    # ==================================================

    search_radius: Decimal = Decimal("0")

    matches: list[RiderMatch] = field(
        default_factory=list,
    )

    ranked_matches: list[RiderMatch] = field(
        default_factory=list,
    )

    # ==================================================
    # Rider Exclusions
    # ==================================================

    excluded_rider_ids: set[Any] = field(
        default_factory=set,
    )

    # ==================================================
    # Results
    # ==================================================

    offer: DeliveryOffer | None = None

    assignment: DeliveryAssignment | None = None

    # ==================================================
    # Metadata
    # ==================================================

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    warnings: list[str] = field(
        default_factory=list,
    )

    errors: list[str] = field(
        default_factory=list,
    )

    # ==================================================
    # Initialization
    # ==================================================

    def __post_init__(self):
        """
        Populate related objects and normalize
        dispatch exclusion state.
        """

        # ----------------------------------------------
        # Customer
        # ----------------------------------------------

        if self.customer is None:
            self.customer = getattr(
                self.delivery,
                "customer",
                None,
            )

        # ----------------------------------------------
        # Vendor
        # ----------------------------------------------

        if self.vendor is None:
            self.vendor = getattr(
                self.delivery,
                "vendor",
                None,
            )

        # ----------------------------------------------
        # Normalize excluded riders
        # ----------------------------------------------
        #
        # Older callers may still provide exclusions
        # through metadata. Merge them into the proper
        # context field and then keep metadata synchronized.

        metadata_excluded = self.metadata.get(
            "excluded_rider_ids",
            set(),
        )

        if metadata_excluded:
            self.excluded_rider_ids.update(
                metadata_excluded,
            )

        self._sync_excluded_riders()

    # ==================================================
    # State
    # ==================================================

    def update_status(
        self,
        status: DispatchStatus,
    ):
        """
        Update the current dispatch status.
        """

        self.status = status

        return self

    def update_step(
        self,
        step: str,
    ):
        """
        Update the current dispatch workflow step.
        """

        self.current_step = step

        return self

    def increment_attempt(
        self,
    ):
        """
        Increment the dispatch attempt counter.
        """

        self.attempt += 1

        return self

    # ==================================================
    # Rider Exclusions
    # ==================================================

    def exclude_rider(
        self,
        rider,
    ):
        """
        Exclude a rider from subsequent matching
        attempts for this dispatch context.
        """

        if rider is None:
            return self

        rider_id = getattr(
            rider,
            "id",
            rider,
        )

        return self.exclude_rider_id(
            rider_id,
        )

    def exclude_rider_id(
        self,
        rider_id,
    ):
        """
        Exclude a rider directly by ID.

        The exclusion is stored in the dedicated
        excluded_rider_ids collection and synchronized
        to metadata for backward compatibility.
        """

        if rider_id is None:
            return self

        self.excluded_rider_ids.add(
            rider_id,
        )

        self._sync_excluded_riders()

        return self

    def exclude_riders(
        self,
        rider_ids,
    ):
        """
        Exclude multiple riders at once.
        """

        if rider_ids:

            self.excluded_rider_ids.update(
                rider_ids,
            )

            self._sync_excluded_riders()

        return self

    def is_rider_excluded(
        self,
        rider,
    ):
        """
        Determine whether a rider has already been
        excluded from this dispatch lifecycle.
        """

        if rider is None:
            return False

        rider_id = getattr(
            rider,
            "id",
            rider,
        )

        return (
            rider_id
            in self.excluded_rider_ids
        )

    def get_excluded_rider_ids(
        self,
    ):
        """
        Return a copy of the excluded rider IDs.

        Returning a copy prevents callers from
        accidentally mutating the context without
        synchronization.
        """

        return set(
            self.excluded_rider_ids,
        )

    def _sync_excluded_riders(
        self,
    ):
        """
        Keep the legacy metadata representation
        synchronized with the dedicated exclusion set.

        New code should use:

            context.excluded_rider_ids

        instead of reading metadata directly.
        """

        self.metadata[
            "excluded_rider_ids"
        ] = self.excluded_rider_ids

    # ==================================================
    # Metadata
    # ==================================================

    def add_metadata(
        self,
        key,
        value,
    ):
        """
        Add metadata to the dispatch context.

        The excluded rider metadata key is handled
        specially so the dedicated exclusion collection
        remains the source of truth.
        """

        if key == "excluded_rider_ids":

            if value:
                self.excluded_rider_ids.update(
                    value,
                )

            self._sync_excluded_riders()

            return self

        self.metadata[key] = value

        return self

    def get_metadata(
        self,
        key,
        default=None,
    ):
        """
        Safely retrieve dispatch metadata.
        """

        return self.metadata.get(
            key,
            default,
        )

    # ==================================================
    # Warnings
    # ==================================================

    def add_warning(
        self,
        message,
    ):
        """
        Add a non-fatal warning.
        """

        self.warnings.append(
            str(message),
        )

        return self

    # ==================================================
    # Errors
    # ==================================================

    def add_error(
        self,
        message,
    ):
        """
        Add an error message.
        """

        self.errors.append(
            str(message),
        )

        return self

    # ==================================================
    # Bulk Update
    # ==================================================

    def set(
        self,
        **kwargs,
    ):
        """
        Update multiple context attributes.

        Special handling is applied to
        excluded_rider_ids so the exclusion state
        remains synchronized.
        """

        for key, value in kwargs.items():

            if key == "excluded_rider_ids":

                self.excluded_rider_ids = set(
                    value or [],
                )

                self._sync_excluded_riders()

                continue

            setattr(
                self,
                key,
                value,
            )

        return self

    # ==================================================
    # Convenience Properties
    # ==================================================

    @property
    def has_matches(
        self,
    ):
        return bool(
            self.matches,
        )

    @property
    def has_ranked_matches(
        self,
    ):
        return bool(
            self.ranked_matches,
        )

    @property
    def has_assignment(
        self,
    ):
        return (
            self.assignment
            is not None
        )

    @property
    def has_offer(
        self,
    ):
        return (
            self.offer
            is not None
        )

    @property
    def has_selected_rider(
        self,
    ):
        return (
            self.selected_rider
            is not None
        )

    @property
    def has_selected_match(
        self,
    ):
        return (
            self.selected_match
            is not None
        )

    @property
    def has_excluded_riders(
        self,
    ):
        return bool(
            self.excluded_rider_ids,
        )

    @property
    def excluded_rider_count(
        self,
    ):
        return len(
            self.excluded_rider_ids,
        )

    @property
    def has_errors(
        self,
    ):
        return bool(
            self.errors,
        )

    @property
    def has_warnings(
        self,
    ):
        return bool(
            self.warnings,
        )