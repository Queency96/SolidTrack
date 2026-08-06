from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User
from customers.models import CustomerProfile
from vendors.models import VendorProfile
from riders.models import RiderProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):

    if not created:
        return

    if instance.role == User.Roles.CUSTOMER:
        CustomerProfile.objects.create(
            user=instance,
            referral_code=f"REF{instance.id.hex[:8].upper()}"
        )

    elif instance.role == User.Roles.VENDOR:
        VendorProfile.objects.create(
            user=instance,
            company_name=""
        )

    elif instance.role == User.Roles.RIDER:
        RiderProfile.objects.create(
            user=instance,
            vehicle_type=RiderProfile.VehicleType.BIKE,
            vehicle_plate_number="",
            nin="",
            driver_license=""
        )