from django.contrib import admin
from .models import Wallet, WalletTransaction


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "balance",
        "is_active",
    )

    search_fields = (
        "user__email",
    )


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "reference",
        "wallet",
        "transaction_type",
        "amount",
        "status",
        "created_at",
    )

    search_fields = (
        "reference",
        "wallet__user__email",
    )

    list_filter = (
        "transaction_type",
        "status",
    )