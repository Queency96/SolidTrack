from django.core.cache import cache
from deliveries.models import DispatchConfiguration


class DispatchConfigurationService:
    CACHE_KEY = "dispatch_configuration"
    CACHE_TIMEOUT = 60 * 30

    @classmethod
    def get_configuration(cls):
        config = cache.get(cls.CACHE_KEY)
        if config:
            return config
        config = (
            DispatchConfiguration.objects
            .filter(is_active=True)
            .first()
        )
        if config is None:
            raise ValueError(
                "No active dispatch configuration."
            )
        cache.set(
            cls.CACHE_KEY,
            config,
            timeout=cls.CACHE_TIMEOUT,
        )
        return config