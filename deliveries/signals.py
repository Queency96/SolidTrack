"""
Delivery-related signals.

Currently handles only one concern: invalidating the
cached dispatch configuration whenever a
DispatchConfiguration row is created, updated, or
deleted.

Why this matters
----------------
DispatchConfigurationService caches the active config for
30 minutes. Without invalidation, admin changes to the
active config (timeout, radius, auto_redispatch, which
config is active) would take up to 30 minutes to take
effect. Silent staleness.

Cache invalidation is best-effort. A failure here does
not roll back the model save/delete.
"""

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import DispatchConfiguration


logger = logging.getLogger(__name__)


# ==================================================
# Save
# ==================================================

@receiver(post_save, sender=DispatchConfiguration)
def invalidate_dispatch_config_on_save(sender, instance, **kwargs):
    """
    Flush the cached dispatch configuration after any
    DispatchConfiguration save.

    Best-effort: a cache failure does not affect the
    model save.
    """

    try:
        from .dispatch.service import DispatchConfigurationService

        DispatchConfigurationService.clear_cache()

    except Exception:

        logger.exception(
            "Failed to invalidate dispatch config cache "
            "after saving config %s.",
            getattr(instance, "pk", None),
        )


# ==================================================
# Delete
# ==================================================

@receiver(post_delete, sender=DispatchConfiguration)
def invalidate_dispatch_config_on_delete(sender, instance, **kwargs):
    """
    Flush the cached dispatch configuration after any
    DispatchConfiguration delete.

    Best-effort: a cache failure does not affect the
    model delete.
    """

    try:
        from .dispatch.service import DispatchConfigurationService

        DispatchConfigurationService.clear_cache()

    except Exception:

        logger.exception(
            "Failed to invalidate dispatch config cache "
            "after deleting config %s.",
            getattr(instance, "pk", None),
        )