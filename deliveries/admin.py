from django.contrib import admin
from .models import DeliveryAssignment, PricingConfiguration


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