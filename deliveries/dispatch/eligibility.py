from django.db.models import Count, Q, QuerySet

from accounts.models import User
from riders.models import RiderProfile


class RiderEligibilityService:
    """
    Determines whether riders are eligible to receive
    delivery offers.

    Responsibilities
    ----------------
    • Active rider verification
    • Rider KYC verification
    • Online/availability checks
    • Minimum rating
    • Active workload limits
    • Vehicle compatibility
    • Previous-offer exclusion
    • Package/capacity compatibility
    • Service-area compatibility

    This service DOES NOT:
    • Calculate distance
    • Score riders
    • Create offers
    • Assign riders
    """

    ACTIVE_ASSIGNMENT_STATUSES = (
        "ASSIGNED",
        "ACCEPTED",
        "EN_ROUTE_PICKUP",
        "ARRIVED_PICKUP",
        "PICKED_UP",
        "OUT_FOR_DELIVERY",
        "ARRIVED_DESTINATION",
    )

    # ==================================================
    # Main Eligibility Query
    # ==================================================

    @classmethod
    def get_available_riders(
        cls,
        context=None,
        delivery=None,
    ) -> QuerySet[User]:
        """
        Return riders eligible for the current dispatch.

        `context` is preferred because it provides access
        to DispatchConfiguration and dispatch metadata.

        `delivery` is retained for compatibility with
        callers that only have a delivery instance.
        """

        if context is not None:
            delivery = context.delivery

        riders = (
            User.objects
            .select_related(
                "rider_profile",
                "location",
                "rider_statistics",
            )
            .annotate(
                active_delivery_count=Count(
                    "delivery_assignments",
                    filter=Q(
                        delivery_assignments__status__in=(
                            cls.ACTIVE_ASSIGNMENT_STATUSES
                        ),
                    ),
                    distinct=True,
                ),
            )
            .filter(
                role=User.Roles.RIDER,
                is_active=True,
                is_verified=True,
                rider_profile__is_online=True,
                rider_profile__is_available=True,
                rider_profile__verification_status=(
                    RiderProfile
                    .VerificationStatus
                    .APPROVED
                ),
            )
        )

        # ----------------------------------------------
        # Configuration filters
        # ----------------------------------------------

        if context is not None:

            riders = cls._filter_by_rating(
                riders,
                context,
            )

            riders = cls._filter_by_workload(
                riders,
                context,
            )

        # ----------------------------------------------
        # Delivery-specific filters
        # ----------------------------------------------

        if delivery is not None:

            riders = cls._filter_by_vehicle(
                riders,
                delivery,
            )

            riders = cls.filter_by_capacity(
                riders,
                delivery,
            )

            riders = cls.filter_by_service_area(
                riders,
                delivery,
            )

        # ----------------------------------------------
        # Previous rider exclusion
        # ----------------------------------------------

        if context is not None:

            riders = cls._exclude_previous_riders(
                riders,
                context,
            )

        return riders.distinct()

    # ==================================================
    # Minimum Rating
    # ==================================================

    @staticmethod
    def _filter_by_rating(
        riders,
        context,
    ):
        """
        Exclude riders whose rating is below
        the configured minimum.

        Rating belongs to RiderProfile.
        """

        minimum_rating = getattr(
            context.config,
            "minimum_rider_rating",
            None,
        )

        if minimum_rating is None:
            return riders

        return riders.filter(
            rider_profile__rating__gte=minimum_rating,
        )

    # ==================================================
    # Workload
    # ==================================================

    @staticmethod
    def _filter_by_workload(
        riders,
        context,
    ):
        """
        Exclude riders who already have the maximum
        number of active deliveries.

        The active_delivery_count annotation is
        calculated once in get_available_riders().
        """

        maximum_active_deliveries = getattr(
            context.config,
            "maximum_active_deliveries",
            None,
        )

        if maximum_active_deliveries is None:
            return riders

        return riders.filter(
            active_delivery_count__lt=(
                maximum_active_deliveries
            )
        )

    # ==================================================
    # Vehicle Compatibility
    # ==================================================

    @staticmethod
    def _filter_by_vehicle(
        riders,
        delivery,
    ):
        """
        Return riders capable of handling
        the requested vehicle type.
        """

        vehicle_type = getattr(
            delivery,
            "vehicle_type",
            None,
        )

        if not vehicle_type:
            return riders

        return riders.filter(
            rider_profile__vehicle_type=vehicle_type,
        )

    # ==================================================
    # Previous Rider Exclusion
    # ==================================================

    @staticmethod
    def _exclude_previous_riders(
        riders,
        context,
    ):
        """
        Exclude riders already attempted during
        the current dispatch lifecycle.
        """

        excluded_rider_ids = (
            context.get_excluded_rider_ids()
        )

        if not excluded_rider_ids:
            return riders

        return riders.exclude(
            id__in=excluded_rider_ids,
        )

    # ==================================================
    # Capacity
    # ==================================================

    @staticmethod
    def filter_by_capacity(
        riders,
        delivery,
    ):
        """
        Filter riders according to package size
        and weight.

        Capacity rules are currently not represented
        on RiderProfile, so no filtering is performed.
        """

        # Reserved for future capacity rules.
        #
        # package_weight = getattr(
        #     delivery,
        #     "package_weight",
        #     None,
        # )
        #
        # package_size = getattr(
        #     delivery,
        #     "package_size",
        #     None,
        # )

        return riders

    # ==================================================
    # Wallet
    # ==================================================

    @staticmethod
    def filter_by_wallet(
        riders,
    ):
        """
        Future:
        Exclude riders that do not satisfy
        wallet/balance requirements.
        """

        return riders

    # ==================================================
    # Service Area
    # ==================================================

    @staticmethod
    def filter_by_service_area(
        riders,
        delivery,
    ):
        """
        Future:
        Restrict riders to supported delivery
        service areas.
        """

        return riders

    # ==================================================
    # Single Rider Eligibility
    # ==================================================

    @classmethod
    def is_eligible(
        cls,
        rider,
        context,
    ):
        """
        Check whether a single rider is eligible
        immediately before an offer is created.

        This is intentionally performed again immediately
        before creating an offer/assignment to protect
        against race conditions.
        """

        # ----------------------------------------------
        # Account
        # ----------------------------------------------

        if not rider.is_active:
            return False

        if not rider.is_verified:
            return False

        if getattr(
            rider,
            "role",
            None,
        ) != User.Roles.RIDER:
            return False

        # ----------------------------------------------
        # Rider Profile
        # ----------------------------------------------

        profile = getattr(
            rider,
            "rider_profile",
            None,
        )

        if profile is None:
            return False

        if not profile.is_online:
            return False

        if not profile.is_available:
            return False

        if (
            profile.verification_status
            != RiderProfile
            .VerificationStatus
            .APPROVED
        ):
            return False

        # ----------------------------------------------
        # Minimum Rating
        # ----------------------------------------------

        minimum_rating = getattr(
            context.config,
            "minimum_rider_rating",
            None,
        )

        if (
            minimum_rating is not None
            and profile.rating < minimum_rating
        ):
            return False

        # ----------------------------------------------
        # Active Workload
        # ----------------------------------------------

        maximum_active_deliveries = getattr(
            context.config,
            "maximum_active_deliveries",
            None,
        )

        if maximum_active_deliveries is not None:

            active_delivery_count = (
                rider.delivery_assignments
                .filter(
                    status__in=(
                        cls.ACTIVE_ASSIGNMENT_STATUSES
                    ),
                    is_active=True,
                )
                .count()
            )

            if (
                active_delivery_count
                >= maximum_active_deliveries
            ):
                return False

        # ----------------------------------------------
        # Vehicle Compatibility
        # ----------------------------------------------

        if not cls._is_vehicle_compatible(
            rider,
            context.delivery,
        ):
            return False

        # ----------------------------------------------
        # Previous Rider Exclusion
        # ----------------------------------------------

        excluded_rider_ids = (
            context.get_excluded_rider_ids()
        )

        if rider.id in excluded_rider_ids:
            return False

        # ----------------------------------------------
        # All Checks Passed
        # ----------------------------------------------

        return True

    # ==================================================
    # Single Rider Vehicle Check
    # ==================================================

    @staticmethod
    def _is_vehicle_compatible(
        rider,
        delivery,
    ):
        """
        Check vehicle compatibility for a single rider.
        """

        vehicle_type = getattr(
            delivery,
            "vehicle_type",
            None,
        )

        if not vehicle_type:
            return True

        profile = getattr(
            rider,
            "rider_profile",
            None,
        )

        if profile is None:
            return False

        return (
            profile.vehicle_type
            == vehicle_type
        )