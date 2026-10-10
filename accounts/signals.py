"""
Account-level signals.

Two responsibilities, both triggered on User creation:

    1. Create the correct profile (customer / vendor / rider).
    2. Create a Wallet for every non-admin, non-staff user.

The two are merged into a single handler so a failure in one
does not silently prevent the other, and so the signal fires
exactly once per User creation.
"""

import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import User
from customers.models import CustomerProfile
from vendors.models import VendorProfile
from riders.models import RiderProfile


logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def provision_new_user(sender, instance, created, **kwargs):
    """
    Provision a newly created user.

    Idempotent: does nothing on updates.
    """

    if not created:
        return

    _create_role_profile(instance)
    _create_wallet_if_eligible(instance)


# ==================================================
# Profile provisioning
# ==================================================

def _create_role_profile(user):

    try:

        if user.role == User.Roles.CUSTOMER:
            CustomerProfile.objects.create(
                user=user,
                referral_code=f"REF{user.id.hex[:8].upper()}",
            )

        elif user.role == User.Roles.VENDOR:
            VendorProfile.objects.create(
                user=user,
                company_name="",
            )

        elif user.role == User.Roles.RIDER:
            RiderProfile.objects.create(
                user=user,
                vehicle_type=RiderProfile.VehicleType.BIKE,
                vehicle_plate_number="",
                nin="",
                driver_license="",
            )

    except Exception:

        logger.exception(
            "Failed to create role profile for user %s "
            "(role=%s).",
            user.pk,
            getattr(user, "role", None),
        )

        # Re-raise so signup fails loudly rather than leaving
        # a user without a profile.
        raise


# ==================================================
# Wallet provisioning
# ==================================================

def _create_wallet_if_eligible(user):

    # Staff and superusers do not need wallets.
    if getattr(user, "is_staff", False):
        return
    if getattr(user, "is_superuser", False):
        return

    # Role-based check.
    role = getattr(user, "role", None)
    role_value = getattr(role, "value", role)

    if str(role_value).upper() == "ADMIN":
        return

    try:
        from wallet.models import Wallet

        Wallet.objects.get_or_create(user=user)

    except Exception:

        logger.exception(
            "Failed to create wallet for user %s.",
            user.pk,
        )

        # Wallet creation is best-effort. Do NOT fail signup
        # because of a wallet issue — the wallet can be
        # created later via the backfill command.