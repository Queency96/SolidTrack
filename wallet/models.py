from decimal import Decimal
from django.db import models
from django.conf import settings
from common.models import TimeStampedModel
import uuid


class Wallet(TimeStampedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet"
    )

    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    is_active = models.BooleanField(
        default=True
    )

    def __str__(self):
        return f"{self.user.email} Wallet"



class WalletTransaction(TimeStampedModel):

    class TransactionType(models.TextChoices):

        DEPOSIT = "DEPOSIT", "Deposit"

        WITHDRAWAL = "WITHDRAWAL", "Withdrawal"

        CREDIT = "CREDIT", "Credit"

        DEBIT = "DEBIT", "Debit"

        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):

        PENDING = "PENDING", "Pending"

        SUCCESS = "SUCCESS", "Success"

        FAILED = "FAILED", "Failed"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    reference = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUCCESS
    )

    def __str__(self):
        return self.reference


