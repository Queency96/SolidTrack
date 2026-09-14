from django.apps import AppConfig


class VendorsConfig(AppConfig):
    name = 'vendors'
    
    def ready(self):
        """Import signals when app is ready."""
        import vendors.signals  # noqa
