from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Any
from accounts.models import User
from deliveries.models.delivery import Delivery
from deliveries.models.delivery_assignment import DeliveryAssignment
from deliveries.models.delivery_offer import DeliveryOffer
from deliveries.models.dispatch_configuration import DispatchConfiguration
from vendors.models import VendorProfile, VendorStore
from .match import RiderMatch
from .status import DispatchStatus


@dataclass(slots=True)
class DispatchContext:
    """
    Shared in-memory state for one dispatch attempt.

    See module docstring in original for full responsibility list.

    Naming
    ------
    The `store` attribute exists for compatibility with existing
    code, but it is populated from `delivery.pickup_store` because
    the Delivery model has no `store` field.
    """

    # ==================================================
    # Core
    # ==================================================

    delivery: Delivery

    config: DispatchConfiguration

    status: DispatchStatus = DispatchStatus.CREATED

    current_step: str = "INITIALIZED"

    attempt: int = 1

    # ==================================================
    # Relationships
    # ==================================================

    customer: User | None = None

    vendor: VendorProfile | None = None

    store: VendorStore | None = None

    selected_rider: User | None = None

    selected_match: RiderMatch | None = None

    # ==================================================
    # Search
    # ==================================================

    search_radius: Decimal = Decimal("0")

    matches: list[RiderMatch] = field(default_factory=list)

    ranked_matches: list[RiderMatch] = field(default_factory=list)

    # ==================================================
    # Rider Exclusions
    # ==================================================

    excluded_rider_ids: set[Any] = field(default_factory=set)

    # ==================================================
    # Results
    # ==================================================

    offer: DeliveryOffer | None = None

    assignment: DeliveryAssignment | None = None

    # ==================================================
    # Metadata
    # ==================================================

    metadata: dict[str, Any] = field(default_factory=dict)

    warnings: list[str] = field(default_factory=list)

    errors: list[str] = field(default_factory=list)

    # ==================================================
    # Initialization
    # ==================================================

    def __post_init__(self):
        """
        Normalize context state after initialization.
        """

        self.attempt = self._normalize_attempt(self.attempt)

        # ----------------------------------------------
        # Delivery relationships
        #
        # NOTE: Delivery has no `store` field. The pickup
        # store is `delivery.pickup_store`. The context
        # attribute remains `store` for compatibility.
        # ----------------------------------------------

        if self.delivery is not None:

            if self.customer is None:
                self.customer = getattr(self.delivery, "customer", None)

            if self.vendor is None:
                self.vendor = getattr(self.delivery, "vendor", None)

            if self.store is None:
                self.store = getattr(self.delivery, "pickup_store", None)

        self.search_radius = self._to_decimal(
            self.search_radius,
            default=Decimal("0"),
        )

        if self.search_radius < Decimal("0"):
            self.search_radius = Decimal("0")

        self.excluded_rider_ids = self._normalize_rider_ids(
            self.excluded_rider_ids,
        )

        self._initialize_vendor_metadata()

        metadata_excluded = self.metadata.get("excluded_rider_ids", set())

        if metadata_excluded:
            self.excluded_rider_ids.update(
                self._normalize_rider_ids(metadata_excluded),
            )

        self._sync_excluded_riders()

        if self.selected_match is not None:
            self.selected_rider = getattr(self.selected_match, "rider", None)

    # ==================================================
    # Attempt
    # ==================================================

    @staticmethod
    def _normalize_attempt(attempt) -> int:
        try:
            attempt = int(attempt)
        except (TypeError, ValueError):
            return 1

        return max(attempt, 1)

    def increment_attempt(self):
        self.attempt += 1
        return self

    # ==================================================
    # Vendor Metadata
    # ==================================================

    def _initialize_vendor_metadata(self):
        vendor_priority = self._to_decimal(
            self.metadata.get("vendor_priority", Decimal("0")),
            default=Decimal("0"),
        )
        self.metadata["vendor_priority"] = max(vendor_priority, Decimal("0"))

        multiplier = self._to_decimal(
            self.metadata.get("vendor_priority_multiplier", Decimal("1")),
            default=Decimal("1"),
        )
        self.metadata["vendor_priority_multiplier"] = min(
            max(multiplier, Decimal("0")),
            Decimal("5"),
        )

    # ==================================================
    # State
    # ==================================================

    def update_status(self, status: DispatchStatus):
        if status is None:
            return self
        self.status = status
        return self

    def update_step(self, step: str):
        if step is None:
            return self
        self.current_step = str(step)
        return self

    # ==================================================
    # Search Radius
    # ==================================================

    def set_search_radius(self, radius):
        radius = self._to_decimal(radius, default=Decimal("0"))
        self.search_radius = max(radius, Decimal("0"))
        return self

    # ==================================================
    # Rider Exclusions
    # ==================================================

    def exclude_rider(self, rider):
        if rider is None:
            return self
        rider_id = getattr(rider, "id", rider)
        return self.exclude_rider_id(rider_id)

    def exclude_rider_id(self, rider_id):
        if rider_id is None:
            return self
        rider_id = self._normalize_rider_id(rider_id)
        if rider_id is None:
            return self
        self.excluded_rider_ids.add(rider_id)
        self._sync_excluded_riders()
        return self

    def exclude_riders(self, rider_ids):
        if not rider_ids:
            return self
        normalized_ids = self._normalize_rider_ids(rider_ids)
        self.excluded_rider_ids.update(normalized_ids)
        self._sync_excluded_riders()
        return self

    def is_rider_excluded(self, rider) -> bool:
        if rider is None:
            return False
        rider_id = getattr(rider, "id", rider)
        return self.is_rider_id_excluded(rider_id)

    def is_rider_id_excluded(self, rider_id) -> bool:
        rider_id = self._normalize_rider_id(rider_id)
        if rider_id is None:
            return False
        return rider_id in self.excluded_rider_ids

    def get_excluded_rider_ids(self):
        return set(self.excluded_rider_ids)

    def _sync_excluded_riders(self):
        self.metadata["excluded_rider_ids"] = set(self.excluded_rider_ids)

    # ==================================================
    # Metadata
    # ==================================================

    def add_metadata(self, key, value):
        if not key:
            return self

        if key == "excluded_rider_ids":
            self.exclude_riders(value)
            return self

        if key == "vendor_priority":
            value = self._to_decimal(value, default=Decimal("0"))
            value = max(value, Decimal("0"))

        elif key == "vendor_priority_multiplier":
            value = self._to_decimal(value, default=Decimal("1"))
            value = min(max(value, Decimal("0")), Decimal("5"))

        self.metadata[key] = value
        return self

    def get_metadata(self, key, default=None):
        return self.metadata.get(key, default)

    def get(self, key, default=None):
        return self.get_metadata(key, default)

    # ==================================================
    # Warnings
    # ==================================================

    def add_warning(self, message):
        if message is None:
            return self
        message = str(message).strip()
        if not message:
            return self
        self.warnings.append(message)
        return self

    # ==================================================
    # Errors
    # ==================================================

    def add_error(self, message):
        if message is None:
            return self
        message = str(message).strip()
        if not message:
            return self
        self.errors.append(message)
        return self

    # ==================================================
    # Bulk Update
    # ==================================================

    def set(self, **kwargs):
        for key, value in kwargs.items():

            if key == "status":
                self.update_status(value)
                continue

            if key == "current_step":
                self.update_step(value)
                continue

            if key == "attempt":
                self.attempt = self._normalize_attempt(value)
                continue

            if key == "search_radius":
                self.set_search_radius(value)
                continue

            if key == "excluded_rider_ids":
                self.excluded_rider_ids = self._normalize_rider_ids(value)
                self._sync_excluded_riders()
                continue

            if key in {"vendor_priority", "vendor_priority_multiplier"}:
                self.add_metadata(key, value)
                continue

            if key == "matches":
                self.set_matches(value)
                continue

            if key == "ranked_matches":
                self.set_ranked_matches(value)
                continue

            if key == "selected_match":
                self.select_match(value)
                continue

            if key == "selected_rider":
                self.selected_rider = value
                continue

            if key == "offer":
                self.set_offer(value)
                continue

            if key == "assignment":
                self.set_assignment(value)
                continue

            setattr(self, key, value)

        return self

    # ==================================================
    # Match Management
    # ==================================================

    def set_matches(self, matches):
        self.matches = list(matches or [])
        return self

    def set_ranked_matches(self, ranked_matches):
        self.ranked_matches = list(ranked_matches or [])
        return self

    def clear_matches(self):
        self.matches.clear()
        self.ranked_matches.clear()
        return self

    # ==================================================
    # Selection
    # ==================================================

    def select_match(self, match: RiderMatch | None):
        self.selected_match = match

        if match is None:
            self.selected_rider = None
            return self

        self.selected_rider = getattr(match, "rider", None)
        return self

    def select_top_match(self):
        top_match = self.top_match
        if top_match is None:
            self.clear_selection()
            return self
        return self.select_match(top_match)

    def clear_selection(self):
        self.selected_rider = None
        self.selected_match = None
        return self

    # ==================================================
    # Offer
    # ==================================================

    def set_offer(self, offer: DeliveryOffer | None):
        self.offer = offer
        return self

    def clear_offer(self):
        self.offer = None
        return self

    # ==================================================
    # Assignment
    # ==================================================

    def set_assignment(self, assignment: DeliveryAssignment | None):
        self.assignment = assignment
        return self

    def clear_assignment(self):
        self.assignment = None
        return self

    # ==================================================
    # Attempt Reset
    # ==================================================

    def reset_attempt_state(self):
        self.status = DispatchStatus.CREATED
        self.current_step = "INITIALIZED"
        self.search_radius = Decimal("0")
        self.matches.clear()
        self.ranked_matches.clear()
        self.selected_rider = None
        self.selected_match = None
        self.offer = None
        self.assignment = None
        return self

    # ==================================================
    # Full Dispatch State Reset
    # ==================================================

    def clear_dispatch_state(self):
        self.reset_attempt_state()
        self.warnings.clear()
        self.errors.clear()
        return self

    # ==================================================
    # Decimal Helper
    # ==================================================

    @staticmethod
    def _to_decimal(value, default=Decimal("0")) -> Decimal:
        if value is None:
            return default

        if isinstance(value, Decimal):
            decimal_value = value
        else:
            try:
                decimal_value = Decimal(str(value))
            except (InvalidOperation, TypeError, ValueError):
                return default

        try:
            if not decimal_value.is_finite():
                return default
        except AttributeError:
            try:
                if not isfinite(float(decimal_value)):
                    return default
            except (TypeError, ValueError, OverflowError):
                return default

        return decimal_value

    # ==================================================
    # Rider ID Helpers
    # ==================================================

    @staticmethod
    def _normalize_rider_id(rider_id):
        if rider_id is None:
            return None

        if isinstance(rider_id, str):
            rider_id = rider_id.strip()
            if not rider_id:
                return None

        return rider_id

    @classmethod
    def _normalize_rider_ids(cls, rider_ids) -> set:
        if not rider_ids:
            return set()

        normalized = set()

        for rider_id in rider_ids:
            rider_id = cls._normalize_rider_id(rider_id)
            if rider_id is not None:
                normalized.add(rider_id)

        return normalized

    # ==================================================
    # Vendor Priority
    # ==================================================

    @property
    def vendor_priority(self) -> Decimal:
        return self._to_decimal(
            self.metadata.get("vendor_priority", Decimal("0")),
            default=Decimal("0"),
        )

    @property
    def vendor_priority_multiplier(self) -> Decimal:
        return self._to_decimal(
            self.metadata.get("vendor_priority_multiplier", Decimal("1")),
            default=Decimal("1"),
        )

    # ==================================================
    # Match Properties
    # ==================================================

    @property
    def has_matches(self) -> bool:
        return bool(self.matches)

    @property
    def match_count(self) -> int:
        return len(self.matches)

    @property
    def has_ranked_matches(self) -> bool:
        return bool(self.ranked_matches)

    @property
    def ranked_match_count(self) -> int:
        return len(self.ranked_matches)

    @property
    def top_match(self) -> RiderMatch | None:
        if not self.ranked_matches:
            return None
        return self.ranked_matches[0]

    # ==================================================
    # Selection Properties
    # ==================================================

    @property
    def has_selected_rider(self) -> bool:
        return self.selected_rider is not None

    @property
    def has_selected_match(self) -> bool:
        return self.selected_match is not None

    # ==================================================
    # Offer / Assignment Properties
    # ==================================================

    @property
    def has_offer(self) -> bool:
        return self.offer is not None

    @property
    def has_assignment(self) -> bool:
        return self.assignment is not None

    # ==================================================
    # Exclusion Properties
    # ==================================================

    @property
    def has_excluded_riders(self) -> bool:
        return bool(self.excluded_rider_ids)

    @property
    def excluded_rider_count(self) -> int:
        return len(self.excluded_rider_ids)

    # ==================================================
    # Error / Warning Properties
    # ==================================================

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    # ==================================================
    # Dispatch State Properties
    # ==================================================

    @property
    def is_created(self) -> bool:
        return self.status == DispatchStatus.CREATED

    @property
    def is_dispatching(self) -> bool:
        return self.status == DispatchStatus.DISPATCHING

    @property
    def is_searching(self) -> bool:
        return self.status == DispatchStatus.SEARCHING

    @property
    def is_matched(self) -> bool:
        return self.status == DispatchStatus.MATCHED

    @property
    def is_ranked(self) -> bool:
        return self.status == DispatchStatus.RANKED

    @property
    def is_offered(self) -> bool:
        return self.status == DispatchStatus.OFFERED

    @property
    def is_failed(self) -> bool:
        return self.status == DispatchStatus.FAILED

    @property
    def is_assigned(self) -> bool:
        return self.has_assignment

    @property
    def is_accepted(self) -> bool:
        return self.status == DispatchStatus.ACCEPTED

    @property
    def is_cancelled(self) -> bool:
        return self.status == DispatchStatus.CANCELLED