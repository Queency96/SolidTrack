import uuid
from decimal import Decimal
from django.db import transaction
from .models import Wallet, WalletTransaction



@staticmethod
def generate_reference(prefix="TXN"):
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

# reference=WalletService.generate_reference("DEP")
# reference=WalletService.generate_reference("WTH")
# reference=WalletService.generate_reference("REF")
# reference=WalletService.generate_reference("PAY")


class WalletService:

    @staticmethod
    @transaction.atomic
    def _update_balance(
        wallet,
        amount,
        transaction_type,
        description="",
        allow_negative=False,
    ):
        """
        Internal method for updating wallet balance and creating
        a transaction record.
        """

        amount = Decimal(str(amount))

        wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)

        balance_before = wallet.balance

        if (
            transaction_type in (
                WalletTransaction.TransactionType.DEBIT,
                WalletTransaction.TransactionType.WITHDRAWAL,
            )
            and not allow_negative
            and balance_before < amount
        ):
            raise ValueError("Insufficient wallet balance.")

        if transaction_type in (
            WalletTransaction.TransactionType.CREDIT,
            WalletTransaction.TransactionType.DEPOSIT,
            WalletTransaction.TransactionType.REFUND,
        ):
            wallet.balance += amount

        elif transaction_type in (
            WalletTransaction.TransactionType.DEBIT,
            WalletTransaction.TransactionType.WITHDRAWAL,
        ):
            wallet.balance -= amount

        else:
            raise ValueError("Invalid transaction type.")

        wallet.save(update_fields=["balance"])

        WalletTransaction.objects.create(
            wallet=wallet,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance,
            reference=WalletService.generate_reference("REF"),
            # reference=str(uuid.uuid4()),
            description=description,
            status=WalletTransaction.Status.SUCCESS,
        )

        return wallet

    @staticmethod
    def credit(wallet, amount, description=""):
        return WalletService._update_balance(
            wallet=wallet,
            amount=amount,
            transaction_type=WalletTransaction.TransactionType.CREDIT,
            description=description,
        )

    @staticmethod
    def debit(wallet, amount, description=""):
        return WalletService._update_balance(
            wallet=wallet,
            amount=amount,
            transaction_type=WalletTransaction.TransactionType.DEBIT,
            description=description,
        )

    @staticmethod
    def deposit(wallet, amount, description="Wallet Deposit"):
        return WalletService._update_balance(
            wallet=wallet,
            amount=amount,
            transaction_type=WalletTransaction.TransactionType.DEPOSIT,
            description=description,
        )

    @staticmethod
    def withdraw(wallet, amount, description="Wallet Withdrawal"):
        return WalletService._update_balance(
            wallet=wallet,
            amount=amount,
            transaction_type=WalletTransaction.TransactionType.WITHDRAWAL,
            description=description,
        )

    @staticmethod
    def refund(wallet, amount, description="Refund"):
        return WalletService._update_balance(
            wallet=wallet,
            amount=amount,
            transaction_type=WalletTransaction.TransactionType.REFUND,
            description=description,
        )