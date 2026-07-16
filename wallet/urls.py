from django.urls import path
from .views import (
    WalletView,
    WalletTransactionView,
)

urlpatterns = [
    path("", WalletView.as_view(), name="wallet"),
    path(
        "transactions/",
        WalletTransactionView.as_view(),
        name="wallet-transactions",
    ),
]