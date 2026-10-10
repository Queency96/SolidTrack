from django.core.cache import cache

from deliveries.models import DispatchConfiguration

from .exceptions import DispatchConfigurationError


class DispatchConfigurationService:
    """
    Provides the active dispatch configuration.

    Configuration is cached to avoid querying the database
    for every dispatch operation.

    Cache invalidation is handled by
    deliveries/signals.py, which listens for
    DispatchConfiguration post_save and post_delete events.
    """

    CACHE_KEY = "dispatch_configuration"

    CACHE_TIMEOUT = 60 * 30

    # ==================================================
    # Get Configuration
    # ==================================================

    @classmethod
    def get_configuration(cls):
        """
        Return the active dispatch configuration.

        Raises
        ------
        DispatchConfigurationError
            If no active configuration exists.
        """

        config = cache.get(cls.CACHE_KEY)

        if config is not None:
            return config

        config = (
            DispatchConfiguration.objects
            .filter(is_active=True)
            .first()
        )

        if config is None:
            raise DispatchConfigurationError(
                "No active dispatch configuration."
            )

        cache.set(
            cls.CACHE_KEY,
            config,
            timeout=cls.CACHE_TIMEOUT,
        )

        return config

    # ==================================================
    # Get Active Config (coordinator-compatible)
    # ==================================================

    @classmethod
    def get_active_config(cls):
        """
        Coordinator-compatible alias.

        Returns None when no active configuration exists,
        so callers can decide how to handle the missing
        configuration. get_configuration() retains the
        raising behaviour for callers that depend on it.
        """

        try:
            return cls.get_configuration()

        except DispatchConfigurationError:
            return None

    # ==================================================
    # Cache Invalidation
    # ==================================================

    @classmethod
    def clear_cache(cls):
        """
        Clear the cached dispatch configuration.

        Called by deliveries/signals.py whenever a
        DispatchConfiguration row is created, updated, or
        deleted.
        """

        cache.delete(cls.CACHE_KEY)