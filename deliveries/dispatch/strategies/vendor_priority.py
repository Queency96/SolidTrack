from decimal import Decimal

from .base import BaseDispatchStrategy


class VendorPriorityDispatchStrategy(
    BaseDispatchStrategy,
):
    """
    Vendor-priority dispatch strategy.

    Designed for deliveries where the vendor has a
    business/SLA priority level.

    Scoring priorities
    ------------------
    1. Rider reliability
    2. Rider rating
    3. Rider acceptance rate
    4. Rider completion rate
    5. Vendor priority
    6. Distance to pickup
    7. Current workload
    8. Rider experience
    9. Cancellation penalty

    Vendor-specific priority is obtained from the
    DispatchContext metadata.

    Supported metadata:

        vendor_priority
        vendor_priority_multiplier

    Higher scores indicate better rider matches.
    """

    # ==================================================
    # Score
    # ==================================================

    def score(
        self,
        context,
        match,
    ) -> Decimal:
        """
        Calculate the vendor-priority dispatch score.
        """

        self.validate_inputs(
            context,
            match,
        )

        config = context.config

        # ==================================================
        # Rider Metrics
        # ==================================================

        rating = self.decimal(
            match.rating,
        )

        acceptance_rate = (
            self._normalize_percentage(
                match.acceptance_rate,
            )
        )

        completion_rate = (
            self._normalize_percentage(
                match.completion_rate,
            )
        )

        cancellation_rate = (
            self._normalize_percentage(
                match.cancellation_rate,
            )
        )

        completed_deliveries = max(
            self.decimal(
                match.completed_deliveries,
            ),
            Decimal("0"),
        )

        active_jobs = max(
            self.decimal(
                match.active_jobs,
            ),
            Decimal("0"),
        )

        distance = max(
            self.decimal(
                match.distance_km,
            ),
            Decimal("0"),
        )

        # ==================================================
        # Configuration Weights
        # ==================================================

        rating_weight = self.decimal(
            config.rating_weight,
        )

        distance_weight = self.decimal(
            config.distance_weight,
        )

        workload_weight = self.decimal(
            config.workload_weight,
        )

        acceptance_weight = self.decimal(
            config.acceptance_rate_weight,
        )

        completion_weight = self.decimal(
            config.completion_rate_weight,
        )

        cancellation_weight = self.decimal(
            config.cancellation_weight,
        )

        experience_weight = self.decimal(
            config.experience_weight,
        )

        # ==================================================
        # Rating
        # ==================================================

        rating_factor = min(
            max(
                rating / Decimal("5"),
                Decimal("0"),
            ),
            Decimal("1"),
        )

        rating_score = (
            rating_factor
            * rating_weight
        )

        # ==================================================
        # Acceptance Rate
        # ==================================================

        acceptance_score = (
            acceptance_rate
            * acceptance_weight
        )

        # ==================================================
        # Completion Rate
        # ==================================================

        completion_score = (
            completion_rate
            * completion_weight
        )

        # ==================================================
        # Cancellation Penalty
        # ==================================================

        cancellation_penalty = (
            cancellation_rate
            * cancellation_weight
        )

        # ==================================================
        # Distance
        # ==================================================

        distance_factor = (
            Decimal("1")
            / (
                Decimal("1")
                + distance
            )
        )

        distance_score = (
            distance_factor
            * distance_weight
        )

        # ==================================================
        # Workload
        # ==================================================

        workload_factor = (
            Decimal("1")
            / (
                Decimal("1")
                + active_jobs
            )
        )

        workload_score = (
            workload_factor
            * workload_weight
        )

        # ==================================================
        # Experience
        # ==================================================

        experience_factor = (
            completed_deliveries
            / (
                completed_deliveries
                + Decimal("100")
            )
        )

        experience_score = (
            experience_factor
            * experience_weight
        )

        # ==================================================
        # Vendor Priority
        # ==================================================

        vendor_priority = (
            self._get_vendor_priority(
                context=context,
                match=match,
            )
        )

        vendor_multiplier = (
            self._get_vendor_multiplier(
                context=context,
                match=match,
            )
        )

        normalized_priority = min(
            vendor_priority,
            Decimal("10"),
        )

        vendor_priority_score = (
            normalized_priority
            * vendor_multiplier
        )

        # ==================================================
        # Rider Reliability
        # ==================================================

        reliability_factor = (
            acceptance_rate
            * completion_rate
            * (
                Decimal("1")
                - cancellation_rate
            )
        )

        reliability_score = (
            reliability_factor
            * (
                acceptance_weight
                + completion_weight
            )
        )

        # ==================================================
        # Vendor Reliability Bonus
        # ==================================================

        vendor_reliability_bonus = (
            reliability_score
            * normalized_priority
            * vendor_multiplier
            / Decimal("10")
        )

        # ==================================================
        # Final Score
        # ==================================================

        score = (
            rating_score
            + acceptance_score
            + completion_score
            + distance_score
            + workload_score
            + experience_score
            + reliability_score
            + vendor_priority_score
            + vendor_reliability_bonus
            - cancellation_penalty
        )

        final_score = max(
            score,
            Decimal("0"),
        )

        # ==================================================
        # Scoring Metadata
        # ==================================================

        match.add_metadata(
            "scoring_strategy",
            "VENDOR_PRIORITY",
        )

        match.add_metadata(
            "vendor_priority",
            vendor_priority,
        )

        match.add_metadata(
            "vendor_priority_multiplier",
            vendor_multiplier,
        )

        match.add_metadata(
            "rating_score",
            rating_score,
        )

        match.add_metadata(
            "acceptance_score",
            acceptance_score,
        )

        match.add_metadata(
            "completion_score",
            completion_score,
        )

        match.add_metadata(
            "distance_score",
            distance_score,
        )

        match.add_metadata(
            "workload_score",
            workload_score,
        )

        match.add_metadata(
            "experience_score",
            experience_score,
        )

        match.add_metadata(
            "reliability_score",
            reliability_score,
        )

        match.add_metadata(
            "vendor_priority_score",
            vendor_priority_score,
        )

        match.add_metadata(
            "vendor_reliability_bonus",
            vendor_reliability_bonus,
        )

        match.add_metadata(
            "cancellation_penalty",
            cancellation_penalty,
        )

        match.add_metadata(
            "final_score",
            final_score,
        )

        return final_score

    # ==================================================
    # Vendor Priority
    # ==================================================

    @staticmethod
    def _get_vendor_priority(
        context,
        match,
    ) -> Decimal:
        """
        Resolve vendor priority.

        Resolution order:

            1. DispatchContext.metadata
            2. DispatchContext.get()
            3. RiderMatch.metadata
            4. Default = 0
        """

        value = None

        # ----------------------------------------------
        # Context metadata
        # ----------------------------------------------

        metadata = getattr(
            context,
            "metadata",
            None,
        )

        if isinstance(metadata, dict):
            value = metadata.get(
                "vendor_priority",
            )

        # ----------------------------------------------
        # Context getter
        # ----------------------------------------------

        if value is None and hasattr(
            context,
            "get",
        ):
            value = context.get(
                "vendor_priority",
                None,
            )

        # ----------------------------------------------
        # Match metadata
        # ----------------------------------------------

        if value is None:
            value = match.get_metadata(
                "vendor_priority",
                0,
            )

        # ----------------------------------------------
        # Normalize
        # ----------------------------------------------

        try:
            value = Decimal(
                str(value)
            )
        except (
            TypeError,
            ValueError,
        ):
            value = Decimal("0")

        return max(
            value,
            Decimal("0"),
        )

    # ==================================================
    # Vendor Multiplier
    # ==================================================

    @staticmethod
    def _get_vendor_multiplier(
        context,
        match,
    ) -> Decimal:
        """
        Resolve vendor priority multiplier.

        Resolution order:

            1. DispatchContext.metadata
            2. DispatchContext.get()
            3. RiderMatch.metadata
            4. Default = 1

        Allowed range:

            0 → 5
        """

        value = None

        # ----------------------------------------------
        # Context metadata
        # ----------------------------------------------

        metadata = getattr(
            context,
            "metadata",
            None,
        )

        if isinstance(metadata, dict):
            value = metadata.get(
                "vendor_priority_multiplier",
            )

        # ----------------------------------------------
        # Context getter
        # ----------------------------------------------

        if value is None and hasattr(
            context,
            "get",
        ):
            value = context.get(
                "vendor_priority_multiplier",
                None,
            )

        # ----------------------------------------------
        # Match metadata
        # ----------------------------------------------

        if value is None:
            value = match.get_metadata(
                "vendor_priority_multiplier",
                1,
            )

        # ----------------------------------------------
        # Normalize
        # ----------------------------------------------

        try:
            value = Decimal(
                str(value)
            )
        except (
            TypeError,
            ValueError,
        ):
            value = Decimal("1")

        # ----------------------------------------------
        # Clamp
        # ----------------------------------------------

        return min(
            max(
                value,
                Decimal("0"),
            ),
            Decimal("5"),
        )

    # ==================================================
    # Percentage Normalization
    # ==================================================

    @staticmethod
    def _normalize_percentage(
        value,
    ) -> Decimal:
        """
        Normalize rate values.

        Supported:

            0
            0.75
            1
            75
            100

        Results:

            0
            0.75
            1
            0.75
            1
        """

        try:
            value = Decimal(
                str(value or 0)
            )
        except (
            TypeError,
            ValueError,
        ):
            return Decimal("0")

        if value <= 0:
            return Decimal("0")

        if value > 1:
            value /= Decimal("100")

        return min(
            value,
            Decimal("1"),
        )