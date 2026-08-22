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

    Vendor priority is dispatch metadata and does NOT
    require fields on VendorProfile.
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
        dispatch state.
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
        # Vendor Dispatch Metadata
        # ----------------------------------------------

        self._initialize_vendor_metadata()

        # ----------------------------------------------
        # Excluded Riders
        # ----------------------------------------------

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
    # Vendor Metadata
    # ==================================================

    def _initialize_vendor_metadata(
        self,
    ):
        """
        Initialize vendor-related dispatch metadata.

        VendorProfile does NOT need dispatch-priority
        fields.

        Priority values are supplied through metadata
        by the dispatch pipeline.

        Defaults:

            vendor_priority = 0
            vendor_priority_multiplier = 1
        """

        # ----------------------------------------------
        # Vendor Priority
        # ----------------------------------------------

        if "vendor_priority" not in self.metadata:
            self.metadata[
                "vendor_priority"
            ] = Decimal("0")

        # ----------------------------------------------
        # Vendor Priority Multiplier
        # ----------------------------------------------

        if (
            "vendor_priority_multiplier"
            not in self.metadata
        ):
            self.metadata[
                "vendor_priority_multiplier"
            ] = Decimal("1")

        # ----------------------------------------------
        # Normalize
        # ----------------------------------------------

        self.metadata[
            "vendor_priority"
        ] = self._to_decimal(
            self.metadata.get(
                "vendor_priority",
                0,
            ),
            default=Decimal("0"),
        )

        self.metadata[
            "vendor_priority_multiplier"
        ] = self._to_decimal(
            self.metadata.get(
                "vendor_priority_multiplier",
                1,
            ),
            default=Decimal("1"),
        )

        # ----------------------------------------------
        # Safety bounds
        # ----------------------------------------------

        self.metadata[
            "vendor_priority"
        ] = max(
            self.metadata[
                "vendor_priority"
            ],
            Decimal("0"),
        )

        self.metadata[
            "vendor_priority_multiplier"
        ] = min(
            max(
                self.metadata[
                    "vendor_priority_multiplier"
                ],
                Decimal("0"),
            ),
            Decimal("5"),
        )

    # ==================================================
    # State
    # ==================================================

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

    # ==================================================
    # Rider Exclusions
    # ==================================================

    def exclude_rider(
        self,
        rider,
    ):
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
        return set(
            self.excluded_rider_ids,
        )

    def _sync_excluded_riders(
        self,
    ):
        self.metadata[
            "excluded_rider_ids"
        ] = set(
            self.excluded_rider_ids,
        )

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

        Vendor priority values are normalized when
        stored.
        """

        # ----------------------------------------------
        # Excluded riders
        # ----------------------------------------------

        if key == "excluded_rider_ids":

            if value:
                self.excluded_rider_ids.update(
                    value,
                )

            self._sync_excluded_riders()

            return self

        # ----------------------------------------------
        # Vendor priority
        # ----------------------------------------------

        if key == "vendor_priority":

            value = self._to_decimal(
                value,
                default=Decimal("0"),
            )

            value = max(
                value,
                Decimal("0"),
            )

        # ----------------------------------------------
        # Vendor multiplier
        # ----------------------------------------------

        elif key == "vendor_priority_multiplier":

            value = self._to_decimal(
                value,
                default=Decimal("1"),
            )

            value = min(
                max(
                    value,
                    Decimal("0"),
                ),
                Decimal("5"),
            )

        self.metadata[key] = value

        return self

    # ==================================================
    # Metadata Retrieval
    # ==================================================

    def get_metadata(
        self,
        key,
        default=None,
    ):
        return self.metadata.get(
            key,
            default,
        )

    # ==================================================
    # Dictionary-Style Metadata Access
    # ==================================================

    def get(
        self,
        key,
        default=None,
    ):
        """
        Dictionary-style access to dispatch metadata.

        Example:

            context.get(
                "vendor_priority",
                0,
            )
        """

        return self.get_metadata(
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
        for key, value in kwargs.items():

            if key == "excluded_rider_ids":

                self.excluded_rider_ids = set(
                    value or [],
                )

                self._sync_excluded_riders()

                continue

            if key == "vendor_priority":

                value = self._to_decimal(
                    value,
                    default=Decimal("0"),
                )

                self.metadata[
                    key
                ] = max(
                    value,
                    Decimal("0"),
                )

                continue

            if (
                key
                == "vendor_priority_multiplier"
            ):

                value = self._to_decimal(
                    value,
                    default=Decimal("1"),
                )

                self.metadata[
                    key
                ] = min(
                    max(
                        value,
                        Decimal("0"),
                    ),
                    Decimal("5"),
                )

                continue

            setattr(
                self,
                key,
                value,
            )

        return self

    # ==================================================
    # Decimal Helper
    # ==================================================

    @staticmethod
    def _to_decimal(
        value,
        default=Decimal("0"),
    ) -> Decimal:
        """
        Safely convert a value to Decimal.
        """

        if value is None:
            return default

        try:
            return Decimal(
                str(value)
            )
        except (
            TypeError,
            ValueError,
        ):
            return default

    # ==================================================
    # Convenience Properties
    # ==================================================

    @property
    def vendor_priority(self) -> Decimal:
        """
        Current vendor dispatch priority.
        """

        return self._to_decimal(
            self.metadata.get(
                "vendor_priority",
                0,
            ),
            default=Decimal("0"),
        )

    @property
    def vendor_priority_multiplier(
        self,
    ) -> Decimal:
        """
        Current vendor priority multiplier.
        """

        return self._to_decimal(
            self.metadata.get(
                "vendor_priority_multiplier",
                1,
            ),
            default=Decimal("1"),
        )

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