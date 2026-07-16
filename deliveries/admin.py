from django.contrib import admin
from .models import DeliveryAssignment, PricingConfiguration, DispatchConfiguration




@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "delivery",
        "rider",
        "status",
        "assigned_by",
        "assigned_at",
    )

    search_fields = (
        "delivery__tracking_number",
        "rider__email",
    )

    list_filter = (
        "status",
        "assigned_at",
    )




@admin.register(PricingConfiguration)
class PricingConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "base_price",
        "price_per_km",
        "service_fee",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )




@admin.register(DispatchConfiguration)
class DispatchConfigurationAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "initial_search_radius_km",
        "maximum_search_radius_km",
        "rider_response_timeout_seconds",
        "auto_redispatch",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )