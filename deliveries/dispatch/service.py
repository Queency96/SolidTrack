from django.core.cache import cache
from deliveries.models import DispatchConfiguration
from .exceptions import DispatchConfigurationError


class DispatchConfigurationService:
    """
    Provides the active dispatch configuration.

    Configuration is cached to avoid querying the database
    for every dispatch operation.
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

        config = cache.get(
            cls.CACHE_KEY,
        )

        if config is not None:
            return config

        config = (
            DispatchConfiguration.objects
            .filter(
                is_active=True,
            )
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