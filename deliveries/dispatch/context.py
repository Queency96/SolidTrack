from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from accounts.models import User
from deliveries.models.delivery_assignment import DeliveryAssignment
from deliveries.models.delivery_offer import DeliveryOffer
from deliveries.models.delivery import Delivery
from deliveries.models.dispatch_configuration import DispatchConfiguration
from vendors.models import VendorProfile, VendorStore
from .match import RiderMatch
from .status import DispatchStatus


@dataclass(slots=True)
class DispatchContext:
    """
    Shared state for the complete dispatch workflow.

    Every dispatch component receives the same context
    instance and updates it throughout the dispatch
    lifecycle.

    Persistent dispatch history remains stored in:

        • DeliveryOffer
        • DeliveryAssignment
        • Delivery
        • Related dispatch models

    This context represents the in-memory state of one
    dispatch attempt.

    Rider matching
    --------------
    RiderMatcher creates RiderMatch objects.

    RiderRaker ranks those RiderMatch objects.

    Therefore:

        matches
            ↓
        RiderMatch objects
            ↓
        RiderRaker
            ↓
        ranked_matches

    Vendor priority is dispatch metadata and does NOT
    require dispatch-priority fields on VendorProfile.
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

    store: VendorStore | None = None

    selected_rider: User | None = None

    selected_match: RiderMatch | None = None

    # ==================================================
    # Search
    # ==================================================

    search_radius: Decimal = Decimal("0")

    # Raw RiderMatch objects returned by RiderMatcher.
    matches: list[RiderMatch] = field(
        default_factory=list,
    )

    # RiderMatch objects after RiderRaker ranking.
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
    # Dispatch Results
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
        Populate related objects and normalize the
        initial dispatch state.
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
        # Vendor store
        # ----------------------------------------------

        if self.store is None:
            self.store = getattr(
                self.delivery,
                "store",
                None,
            )

        # ----------------------------------------------
        # Vendor metadata
        # ----------------------------------------------

        self._initialize_vendor_metadata()

        # ----------------------------------------------
        # Normalize excluded riders
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

        VendorProfile does not need dispatch-priority
        fields.

        Priority values are supplied through dispatch
        metadata.

        Defaults:

            vendor_priority = 0
            vendor_priority_multiplier = 1

        Safety bounds:

            vendor_priority >= 0

            0 <= vendor_priority_multiplier <= 5
        """

        # ----------------------------------------------
        # Vendor priority
        # ----------------------------------------------

        if "vendor_priority" not in self.metadata:

            self.metadata[
                "vendor_priority"
            ] = Decimal("0")

        # ----------------------------------------------
        # Vendor priority multiplier
        # ----------------------------------------------

        if (
            "vendor_priority_multiplier"
            not in self.metadata
        ):

            self.metadata[
                "vendor_priority_multiplier"
            ] = Decimal("1")

        # ----------------------------------------------
        # Normalize priority
        # ----------------------------------------------

        vendor_priority = self._to_decimal(
            self.metadata.get(
                "vendor_priority",
                0,
            ),
            default=Decimal("0"),
        )

        self.metadata[
            "vendor_priority"
        ] = max(
            vendor_priority,
            Decimal("0"),
        )

        # ----------------------------------------------
        # Normalize multiplier
        # ----------------------------------------------

        multiplier = self._to_decimal(
            self.metadata.get(
                "vendor_priority_multiplier",
                1,
            ),
            default=Decimal("1"),
        )

        self.metadata[
            "vendor_priority_multiplier"
        ] = min(
            max(
                multiplier,
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
        Update the current dispatch pipeline step.
        """

        self.current_step = str(step)

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
        Exclude a rider from the current dispatch
        lifecycle.
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
        Exclude a rider by ID.
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
        Exclude multiple riders.
        """

        if not rider_ids:
            return self

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
        Determine whether a rider is excluded.
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

    def is_rider_id_excluded(
        self,
        rider_id,
    ):
        """
        Determine whether a rider ID is excluded.
        """

        if rider_id is None:
            return False

        return (
            rider_id
            in self.excluded_rider_ids
        )

    def get_excluded_rider_ids(
        self,
    ):
        """
        Return a copy of the excluded rider IDs.
        """

        return set(
            self.excluded_rider_ids,
        )

    def _sync_excluded_riders(
        self,
    ):
        """
        Synchronize excluded rider IDs into metadata.
        """

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

        Special handling is applied to:

            • excluded_rider_ids
            • vendor_priority
            • vendor_priority_multiplier
        """

        # ----------------------------------------------
        # Excluded riders
        # ----------------------------------------------

        if key == "excluded_rider_ids":

            self.excluded_rider_ids.update(
                value or [],
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
        """
        Retrieve metadata safely.
        """

        return self.metadata.get(
            key,
            default,
        )

    def get(
        self,
        key,
        default=None,
    ):
        """
        Dictionary-style metadata access.
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
        """
        Add a non-fatal dispatch warning.
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
        Add a dispatch error.
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
        Update multiple context values.

        Special handling exists for:

            • excluded_rider_ids
            • vendor_priority
            • vendor_priority_multiplier
            • matches
            • ranked_matches
        """

        for key, value in kwargs.items():

            # ------------------------------------------
            # Excluded riders
            # ------------------------------------------

            if key == "excluded_rider_ids":

                self.excluded_rider_ids = set(
                    value or [],
                )

                self._sync_excluded_riders()

                continue

            # ------------------------------------------
            # Vendor priority
            # ------------------------------------------

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

            # ------------------------------------------
            # Vendor multiplier
            # ------------------------------------------

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

            # ------------------------------------------
            # Rider matches
            # ------------------------------------------

            if key == "matches":

                self.matches = list(
                    value or [],
                )

                continue

            # ------------------------------------------
            # Ranked RiderMatch objects
            # ------------------------------------------

            if key == "ranked_matches":

                self.ranked_matches = list(
                    value or [],
                )

                continue

            # ------------------------------------------
            # Normal context attribute
            # ------------------------------------------

            setattr(
                self,
                key,
                value,
            )

        return self

    # ==================================================
    # Match Management
    # ==================================================

    def set_matches(
        self,
        matches,
    ):
        """
        Replace the current raw RiderMatch collection.
        """

        self.matches = list(
            matches or [],
        )

        return self

    def set_ranked_matches(
        self,
        ranked_matches,
    ):
        """
        Replace the ranked RiderMatch collection.

        RiderRaker is responsible for determining the
        ranking order.
        """

        self.ranked_matches = list(
            ranked_matches or [],
        )

        return self

    def clear_matches(
        self,
    ):
        """
        Clear both raw and ranked rider matches.
        """

        self.matches.clear()
        self.ranked_matches.clear()

        return self

    # ==================================================
    # Selection
    # ==================================================

    def select_match(
        self,
        match: RiderMatch | None,
    ):
        """
        Select a RiderMatch and synchronize the selected
        rider.
        """

        self.selected_match = match

        if match is None:
            self.selected_rider = None
            return self

        self.selected_rider = getattr(
            match,
            "rider",
            None,
        )

        return self

    def clear_selection(
        self,
    ):
        """
        Clear the currently selected rider/match/offer.

        Useful when a dispatch attempt is restarted or
        redispatched.
        """

        self.selected_rider = None
        self.selected_match = None
        self.offer = None

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
                str(value),
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

    # ==================================================
    # Vendor Priority
    # ==================================================

    @property
    def vendor_priority(
        self,
    ) -> Decimal:
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

    # ==================================================
    # Match Properties
    # ==================================================

    @property
    def has_matches(
        self,
    ):
        """
        True when RiderMatcher returned matches.
        """

        return bool(
            self.matches,
        )

    @property
    def match_count(
        self,
    ):
        """
        Number of raw RiderMatch objects.
        """

        return len(
            self.matches,
        )

    @property
    def has_ranked_matches(
        self,
    ):
        """
        True when RiderRaker produced ranked matches.
        """

        return bool(
            self.ranked_matches,
        )

    @property
    def ranked_match_count(
        self,
    ):
        """
        Number of ranked RiderMatch objects.
        """

        return len(
            self.ranked_matches,
        )

    @property
    def top_match(
        self,
    ) -> RiderMatch | None:
        """
        Return the highest-ranked RiderMatch.

        RiderRaker is responsible for ensuring that
        ranked_matches are ordered correctly.
        """

        if not self.ranked_matches:
            return None

        return self.ranked_matches[0]

    # ==================================================
    # Selection Properties
    # ==================================================

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

    # ==================================================
    # Offer / Assignment Properties
    # ==================================================

    @property
    def has_offer(
        self,
    ):
        return (
            self.offer
            is not None
        )

    @property
    def has_assignment(
        self,
    ):
        return (
            self.assignment
            is not None
        )

    # ==================================================
    # Exclusion Properties
    # ==================================================

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

    # ==================================================
    # Error / Warning Properties
    # ==================================================

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