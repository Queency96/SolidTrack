from django.conf import settings
from .google import GoogleMapsProvider
from .mapbox import MapboxProvider
from .openroute import OpenRouteServiceProvider



class MapProviderFactory:
    _provider = None

    @classmethod
    def get_provider(cls):
        if cls._provider is None:
            provider_name = getattr(
                settings,
                "MAP_PROVIDER",
                "OPENROUTE",
            )

            provider_class = cls.PROVIDERS.get(provider_name)

            if provider_class is None:
                raise ValueError(
                    f"Unknown map provider: {provider_name}"
                )

            cls._provider = provider_class()

        return cls._provider