from django.contrib import admin

from riders.models import (
    PlatformCommission,
    RiderEarning,
)


# ==================================================
# Rider Earning
# ==================================================

@admin.register(RiderEarning)
class RiderEarningAdmin(admin.ModelAdmin):
    """
    Admin for the rider earning ledger.

    Rows are created automatically when an assignment
    completes and settled by the
    wallet.settle_rider_earnings Celery task.

    Admins inspect and retry; they do not create.
    """

    list_display = (
        "id",
        "rider",
        "assignment",
        "gross_amount",
        "commission_amount",
        "net_amount",
        "status",
        "settled_at",
        "created_at",
    )

    list_filter = (
        "status",
        "currency",
        "created_at",
    )

    search_fields = (
        "rider__email",
        "assignment__delivery__tracking_number",
    )

    list_select_related = (
        "rider",
        "assignment",
        "wallet_transaction",
    )

    ordering = ("-created_at",)

    list_per_page = 50

    readonly_fields = (
        "id",
        "rider",
        "assignment",
        "gross_amount",
        "commission_amount",
        "net_amount",
        "currency",
        "wallet_transaction",
        "settled_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "id",
                    "rider",
                    "assignment",
                ),
            },
        ),
        (
            "Amounts",
            {
                "fields": (
                    "gross_amount",
                    "commission_amount",
                    "net_amount",
                    "currency",
                ),
            },
        ),
        (
            "Settlement",
            {
                "fields": (
                    "status",
                    "wallet_transaction",
                    "settled_at",
                    "failure_reason",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    # ------------------------------------------------------
    # Permissions
    # ------------------------------------------------------

    def has_add_permission(self, request):
        # Rows are created by the assignment completion path.
        return False

    def has_change_permission(self, request, obj=None):
        # Row contents are historical; settlement is a task
        # responsibility.
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow deletion only for superusers, e.g. cleanup.
        return request.user.is_superuser


# ==================================================
# Platform Commission
# ==================================================

@admin.register(PlatformCommission)
class PlatformCommissionAdmin(admin.ModelAdmin):
    """
    Admin for platform commission configuration.

    Only one row should be active at a time; the effective
    rate is the most recently created row with
    is_active=True.

    Historical earnings snapshot their commission, so
    changing the active rate does not affect past rows.
    """

    list_display = (
        "name",
        "percentage",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "-is_active",
        "-created_at",
    )

    # ------------------------------------------------------
    # Form safety
    # ------------------------------------------------------

    def save_model(self, request, obj, form, change):
        """
        When activating a commission row, deactivate every
        other active row. Enforces the single-active-config
        invariant at the admin layer.
        """

        super().save_model(request, obj, form, change)

        if obj.is_active:

            PlatformCommission.objects.exclude(
                pk=obj.pk,
            ).filter(
                is_active=True,
            ).update(
                is_active=False,
            )