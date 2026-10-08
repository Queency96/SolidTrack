"""
Wallet operations service.

This module is the single entry point for mutating
Wallet.balance. Every balance change is recorded as a
WalletTransaction row that stores the balance before and
after the change, so the wallet ledger is fully auditable
and replayable.

Concurrency
-----------
Balance changes are serialized by locking the Wallet row
with SELECT ... FOR UPDATE. Callers must wrap operations
in a transaction (the service does this itself via the
`@transaction.atomic` decorator on each entry point).

Idempotency
-----------
Every mutating call requires a `reference`. The
WalletTransaction.reference column is UNIQUE at the
database level. If a call is replayed with the same
reference, the service returns the existing transaction
instead of crediting/debiting twice.

This makes it safe to retry from a queue, from a webhook
handler, or from within a Django admin action.

Design notes
------------
- The service does NOT decide *when* to credit/debit. That
  is a business concern owned by callers
  (CheckoutService, RefundService, payout flows, etc).
- The service DOES own:
    * balance arithmetic
    * row locking
    * WalletTransaction persistence
    * idempotency enforcement
    * validation of amount / reference / status
- RefundService intentionally writes its own
  WalletTransaction rows (with a deterministic
  REF-FULFILLMENT-<uuid> reference) rather than calling
  WalletService.credit(). That keeps refunds independent
  of any change to this service.
"""

from __future__ import annotations

import logging

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from wallet.models import (
    Wallet,
    WalletTransaction,
)


logger = logging.getLogger(__name__)


class InsufficientBalance(ValidationError):
    """
    Raised when a debit would take the wallet below zero.
    """


class WalletService:
    """
    Primitive credit/debit operations on a customer wallet.

    All public methods are classmethods and are atomic.
    """

    # ==================================================
    # Constants
    # ==================================================

    # Minimum positive amount accepted by credit/debit.
    MIN_AMOUNT = Decimal("0.01")

    # Maximum single-transaction amount. Guards against
    # accidental over-credits from webhook replays or
    # fat-fingered admin actions.
    MAX_AMOUNT = Decimal("10000000.00")  # ₦10,000,000

    # ==================================================
    # Wallet lifecycle
    # ==================================================

    @classmethod
    def get_or_create_wallet(
        cls,
        *,
        user,
    ) -> Wallet:
        """
        Return the user's wallet, creating one with a zero
        balance if it does not exist.

        Safe under concurrent first-time access: the
        OneToOneField on Wallet.user makes the second
        create fail with IntegrityError, which we catch
        and translate into a re-fetch.
        """

        if user is None:
            raise ValidationError("User is required.")

        try:
            return Wallet.objects.get(user=user)
        except Wallet.DoesNotExist:
            pass

        try:
            return Wallet.objects.create(
                user=user,
                balance=Decimal("0.00"),
                is_active=True,
            )
        except IntegrityError:
            # Another worker created it first.
            return Wallet.objects.get(user=user)

    # ==================================================
    # Public primitives
    # ==================================================

    @classmethod
    @transaction.atomic
    def credit(
        cls,
        *,
        wallet,
        amount,
        reference,
        description="",
        transaction_type=WalletTransaction.TransactionType.CREDIT,
    ) -> WalletTransaction:
        """
        Add `amount` to the wallet balance.

        Idempotent: replaying with the same `reference`
        returns the existing transaction unchanged.
        """

        return cls._apply(
            wallet=wallet,
            amount=amount,
            reference=reference,
            description=description,
            transaction_type=transaction_type,
            direction="credit",
        )

    # ==================================================

    @classmethod
    @transaction.atomic
    def debit(
        cls,
        *,
        wallet,
        amount,
        reference,
        description="",
        transaction_type=WalletTransaction.TransactionType.DEBIT,
    ) -> WalletTransaction:
        """
        Subtract `amount` from the wallet balance.

        Idempotent: replaying with the same `reference`
        returns the existing transaction unchanged.

        Raises InsufficientBalance if the wallet would go
        below zero.
        """

        return cls._apply(
            wallet=wallet,
            amount=amount,
            reference=reference,
            description=description,
            transaction_type=transaction_type,
            direction="debit",
        )

    # ==================================================
    # Convenience wrappers
    # ==================================================

    @classmethod
    @transaction.atomic
    def deposit(
        cls,
        *,
        user,
        amount,
        reference,
        description="",
    ) -> WalletTransaction:
        """
        Credit a user's wallet (top-up, funding, admin grant).
        """

        wallet = cls._lock_wallet_for_user(user=user)

        return cls.credit(
            wallet=wallet,
            amount=amount,
            reference=reference,
            description=description,
            transaction_type=(
                WalletTransaction.TransactionType.DEPOSIT
            ),
        )

    # ==================================================

    @classmethod
    @transaction.atomic
    def withdraw(
        cls,
        *,
        user,
        amount,
        reference,
        description="",
    ) -> WalletTransaction:
        """
        Debit a user's wallet (payout, cash-out).
        """

        wallet = cls._lock_wallet_for_user(user=user)

        return cls.debit(
            wallet=wallet,
            amount=amount,
            reference=reference,
            description=description,
            transaction_type=(
                WalletTransaction.TransactionType.WITHDRAWAL
            ),
        )

    # ==================================================
    # Balance queries
    # ==================================================

    @staticmethod
    def get_balance(*, wallet) -> Decimal:
        """
        Return the current wallet balance.

        Reads from the Wallet row, not from the last
        transaction, so it reflects any in-flight updates.
        """

        if wallet is None:
            raise ValidationError("Wallet is required.")

        return Wallet.objects.values_list(
            "balance",
            flat=True,
        ).get(pk=wallet.pk)

    # ==================================================
    # Internal: apply a mutation
    # ==================================================

    @classmethod
    def _apply(
        cls,
        *,
        wallet,
        amount,
        reference,
        description,
        transaction_type,
        direction,
    ) -> WalletTransaction:
        """
        Lock the wallet row, check idempotency, compute the
        new balance, and write the transaction row.
        """

        if wallet is None:
            raise ValidationError("Wallet is required.")

        amount = cls._normalize_amount(amount)
        reference = cls._normalize_reference(reference)
        description = str(description or "")

        # --------------------------------------------------
        # Idempotency: return the existing transaction if
        # the reference has already been used.
        # --------------------------------------------------

        existing = (
            WalletTransaction.objects
            .filter(reference=reference)
            .first()
        )

        if existing is not None:
            logger.info(
                "Wallet transaction %s already exists "
                "(reference=%s); returning existing row.",
                existing.pk,
                reference,
            )
            return existing

        # --------------------------------------------------
        # Lock the wallet row for the balance update.
        # --------------------------------------------------

        locked_wallet = (
            Wallet.objects
            .select_for_update()
            .get(pk=wallet.pk)
        )

        if not locked_wallet.is_active:
            raise ValidationError(
                "Wallet is inactive."
            )

        balance_before = locked_wallet.balance

        if direction == "credit":

            balance_after = (
                balance_before + amount
            ).quantize(Decimal("0.01"))

        else:

            balance_after = (
                balance_before - amount
            ).quantize(Decimal("0.01"))

            if balance_after < Decimal("0.00"):

                raise InsufficientBalance(
                    {
                        "amount": (
                            "Insufficient wallet balance "
                            f"(have {balance_before}, need "
                            f"{amount})."
                        )
                    }
                )

        # --------------------------------------------------
        # Write the transaction. The UNIQUE constraint on
        # reference is our final defense against a race
        # between two workers using the same reference.
        # --------------------------------------------------

        try:

            transaction_row = (
                WalletTransaction.objects.create(
                    wallet=locked_wallet,
                    transaction_type=transaction_type,
                    amount=amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    reference=reference,
                    description=description,
                    status=(
                        WalletTransaction.Status.SUCCESS
                    ),
                )
            )

        except IntegrityError:

            # Another worker won the race. Return the
            # existing row so the caller sees the same
            # result as an idempotent replay.
            existing = (
                WalletTransaction.objects
                .filter(reference=reference)
                .first()
            )

            if existing is not None:
                return existing

            raise

        # --------------------------------------------------
        # Persist the new balance.
        # --------------------------------------------------

        locked_wallet.balance = balance_after

        locked_wallet.save(
            update_fields=[
                "balance",
                "updated_at",
            ],
        )

        logger.info(
            "Wallet %s %s %s (balance %s -> %s, ref=%s)",
            locked_wallet.pk,
            direction,
            amount,
            balance_before,
            balance_after,
            reference,
        )

        return transaction_row

    # ==================================================
    # Internal: helpers
    # ==================================================

    @staticmethod
    def _lock_wallet_for_user(*, user) -> Wallet:
        """
        Return the user's wallet, locked for update.

        Creates the wallet if it does not exist.
        """

        if user is None:
            raise ValidationError("User is required.")

        try:

            return (
                Wallet.objects
                .select_for_update()
                .get(user=user)
            )

        except Wallet.DoesNotExist:

            # Create outside the SELECT ... FOR UPDATE
            # path. The OneToOne constraint protects us
            # from duplicate creation.
            try:
                Wallet.objects.create(
                    user=user,
                    balance=Decimal("0.00"),
                    is_active=True,
                )
            except IntegrityError:
                pass

            return (
                Wallet.objects
                .select_for_update()
                .get(user=user)
            )

    # ==================================================

    @classmethod
    def _normalize_amount(cls, amount) -> Decimal:
        """
        Coerce to Decimal, quantize to 2 places, and
        enforce the min/max bounds.
        """

        if amount is None:
            raise ValidationError(
                {"amount": "Amount is required."}
            )

        try:
            amount = Decimal(str(amount))

        except (TypeError, ValueError):
            raise ValidationError(
                {"amount": "Amount must be a valid number."}
            )

        amount = amount.quantize(Decimal("0.01"))

        if amount <= Decimal("0.00"):
            raise ValidationError(
                {
                    "amount": (
                        "Amount must be greater than zero."
                    )
                }
            )

        if amount < cls.MIN_AMOUNT:
            raise ValidationError(
                {
                    "amount": (
                        f"Amount must be at least "
                        f"{cls.MIN_AMOUNT}."
                    )
                }
            )

        if amount > cls.MAX_AMOUNT:
            raise ValidationError(
                {
                    "amount": (
                        f"Amount cannot exceed "
                        f"{cls.MAX_AMOUNT}."
                    )
                }
            )

        return amount

    # ==================================================

    @classmethod
    def _normalize_reference(cls, reference) -> str:
        """
        Coerce to a non-empty string, bounded by the
        WalletTransaction.reference column length.
        """

        if reference is None:
            raise ValidationError(
                {"reference": "Reference is required."}
            )

        reference = str(reference).strip()

        if not reference:
            raise ValidationError(
                {
                    "reference": (
                        "Reference cannot be empty."
                    )
                }
            )

        if len(reference) > 100:
            raise ValidationError(
                {
                    "reference": (
                        "Reference cannot exceed "
                        "100 characters."
                    )
                }
            )

        return reference