from accounts.models import User 


class RiderEligibilityService:

    @staticmethod
    def get_available_riders():

        return User.objects.filter(
            role=User.Roles.RIDER,
            is_active=True,
            is_verified=True,
            rider_profile__is_online=True,
            rider_profile__is_available=True,
            rider_profile__kyc_status="APPROVED",
        )