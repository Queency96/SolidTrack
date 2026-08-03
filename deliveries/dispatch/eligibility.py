from django.db.models import QuerySet
from accounts.models import User


class RiderEligibilityService:
    """
    Determines whether a rider is eligible
    to receive delivery offers.
    """

    @classmethod
    def get_available_riders(
        cls,
        delivery=None,
    ) -> QuerySet[User]:
        """
        Returns riders that satisfy the
        minimum eligibility requirements.
        """

        riders = (
            User.objects
            .select_related(
                "rider_profile",
            )
            .filter(
                role=User.Roles.RIDER,
                is_active=True,
                is_verified=True,
                rider_profile__is_online=True,
                rider_profile__is_available=True,
                rider_profile__kyc_status="APPROVED",
            )
        )

        if delivery:
            riders = cls._filter_by_vehicle(
                riders,
                delivery,
            )

        return riders

    # ------------------------------------------
    # Vehicle Compatibility
    # ------------------------------------------

    @staticmethod
    def _filter_by_vehicle(
        riders,
        delivery,
    ):
        """
        Return riders that can handle
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

    # ------------------------------------------
    # Future Filters
    # ------------------------------------------

    @staticmethod
    def filter_by_capacity(
        riders,
        delivery,
    ):
        """
        Future:
        Check package size / weight.
        """
        return riders

    @staticmethod
    def filter_by_workload(
        riders,
    ):
        """
        Future:
        Exclude riders handling too many
        active deliveries.
        """
        return riders

    @staticmethod
    def filter_by_wallet(
        riders,
    ):
        """
        Future:
        Exclude riders with insufficient
        wallet balance.
        """
        return riders

    @staticmethod
    def filter_by_service_area(
        riders,
        delivery,
    ):
        """
        Future:
        Restrict riders to supported
        service areas.
        """
        return riders