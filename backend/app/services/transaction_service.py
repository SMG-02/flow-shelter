"""Transactions and the "mark received / mark paid" confirmations.

Every query is scoped by `user_id`.

Confirming an income marks the matching `expected_incomes` row 'received' and
confirming an expense marks the matching `financial_commitments` row paid.
Those rows then drop out of the forecast (dashboard and cash flow both only
count 'expected' / unpaid), so the same money is never projected twice.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.expected_income import ExpectedIncome
from app.models.financial_commitment import FinancialCommitment
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionIn,
    TransactionOptions,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)

ZERO = Decimal("0.00")


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    """The row is not in a state that allows the requested change."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---- create / read / update / delete --------------------------------------
def create(db: Session, user_id: int, data: TransactionIn) -> Transaction:
    tx = Transaction(
        user_id=user_id,
        **data.model_dump(),
    )
    if data.status == "received":
        tx.confirmed_at = _now()
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def _get_owned(db: Session, user_id: int, transaction_id: int) -> Transaction:
    tx = db.scalar(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id,
        )
    )
    if tx is None:
        raise NotFoundError(transaction_id)
    return tx


def get(db: Session, user_id: int, transaction_id: int) -> Transaction:
    return _get_owned(db, user_id, transaction_id)


def update(
    db: Session, user_id: int, transaction_id: int, patch: TransactionUpdate
) -> Transaction:
    tx = _get_owned(db, user_id, transaction_id)
    changes = patch.model_dump(exclude_unset=True)

    if "status" in changes and changes["status"] != tx.status:
        if tx.is_savings_allocation:
            raise ConflictError("A savings allocation cannot change status.")
        tx.confirmed_at = _now() if changes["status"] == "received" else None

    for field, value in changes.items():
        setattr(tx, field, value)

    db.commit()
    db.refresh(tx)
    return tx


def delete(db: Session, user_id: int, transaction_id: int) -> None:
    tx = _get_owned(db, user_id, transaction_id)
    if tx.is_savings_allocation:
        raise ConflictError("Savings allocations are derived, not stored.")
    db.delete(tx)
    db.commit()


def _month_bounds(month: str | None) -> tuple[date, date, str]:
    today = date.today()
    if month:
        try:
            year, mon = (int(part) for part in month.split("-"))
            first = date(year, mon, 1)
        except (ValueError, TypeError):
            raise ValueError("month must look like 2025-06") from None
    else:
        first = today.replace(day=1)

    if first.month == 12:
        following = date(first.year + 1, 1, 1)
    else:
        following = date(first.year, first.month + 1, 1)
    return first, following, f"{first.year:04d}-{first.month:02d}"


def list_transactions(
    db: Session,
    user_id: int,
    month: str | None = None,
    from_date: date | None = None,
    kind: str = "all",
) -> TransactionPage:
    """One month (default: the current one), newest first.

    `from_date` matches the screen's "From date (optional)" filter and is
    applied inside the month, so the list stays a single-period view.
    """

    first, following, month_key = _month_bounds(month)

    if kind not in ("all", "income", "expenses"):
        raise ValueError("kind must be all, income or expenses")

    filters = [
        Transaction.user_id == user_id,
        Transaction.transaction_date >= first,
        Transaction.transaction_date < following,
    ]
    if from_date is not None:
        filters.append(Transaction.transaction_date >= max(from_date, first))
    if kind != "all":
        wanted = "income" if kind == "income" else "expense"
        filters.append(Transaction.direction == wanted)

    rows = list(
        db.scalars(
            select(Transaction)
            .where(*filters)
            .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        )
    )

    # Totals cover every row in the filter, including expected ones, since
    # the screen is a record of the month, not a confirmed balance.
    income = sum(
        (row.amount for row in rows if row.direction == "income"), ZERO
    )
    expenses = sum(
        (row.amount for row in rows if row.direction == "expense"), ZERO
    )

    return TransactionPage(
        items=[TransactionOut.model_validate(row) for row in rows],
        total_income=income,
        total_expenses=expenses,
        net=income - expenses,
        month=month_key,
    )


def options() -> TransactionOptions:
    return TransactionOptions.defaults()


# ---- confirmations --------------------------------------------------------
def _confirm_expected_payment(
    db: Session, user_id: int, income_id: int, received_on: date
) -> Transaction:
    income = db.scalar(
        select(ExpectedIncome).where(
            ExpectedIncome.id == income_id,
            ExpectedIncome.user_id == user_id,
        )
    )
    if income is None:
        raise NotFoundError(income_id)
    if income.status != "expected":
        raise ConflictError(f"This payment is already {income.status}.")

    income.status = "received"
    tx = Transaction(
        user_id=user_id,
        direction="income",
        description=income.source,
        amount=income.amount,
        transaction_date=received_on,
        status="received",
        category="client_payment",
        confirmed_at=date.today(),
        source_income_id=income.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def _confirm_commitment(
    db: Session, user_id: int, commitment_id: int, paid_on: date
) -> Transaction:
    commitment = db.scalar(
        select(FinancialCommitment).where(
            FinancialCommitment.id == commitment_id,
            FinancialCommitment.user_id == user_id,
        )
    )
    if commitment is None:
        raise NotFoundError(commitment_id)
    if commitment.is_paid:
        raise ConflictError("This commitment is already marked paid.")

    commitment.is_paid = True
    tx = Transaction(
        user_id=user_id,
        direction="expense",
        description=commitment.name,
        amount=commitment.amount,
        transaction_date=paid_on,
        status="received",
        category="housing",
        confirmed_at=date.today(),
        source_commitment_id=commitment.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def mark_income_received(
    db: Session, user_id: int, income_id: int, received_on: date | None = None
) -> Transaction:
    return _confirm_expected_payment(db, user_id, income_id, received_on or date.today())


def mark_commitment_paid(
    db: Session, user_id: int, commitment_id: int, paid_on: date | None = None
) -> Transaction:
    return _confirm_commitment(db, user_id, commitment_id, paid_on or date.today())


def mark_transaction_received(
    db: Session, user_id: int, transaction_id: int
) -> Transaction:
    """The Transactions screen's "Mark received"/"Mark paid" button."""

    tx = _get_owned(db, user_id, transaction_id)
    if tx.is_savings_allocation:
        raise ConflictError("A savings allocation cannot be confirmed.")
    if tx.status != "expected":
        raise ConflictError(f"This transaction is already {tx.status}.")

    tx.status = "received"
    tx.confirmed_at = date.today()

    # Link back to the onboarding record this transaction came from, if any,
    # so the forecast stops counting it twice.
    if tx.source_income_id is not None:
        income = db.get(ExpectedIncome, tx.source_income_id)
        if income is not None and income.status == "expected":
            income.status = "received"
    if tx.source_commitment_id is not None:
        commitment = db.get(FinancialCommitment, tx.source_commitment_id)
        if commitment is not None and not commitment.is_paid:
            commitment.is_paid = True

    db.commit()
    db.refresh(tx)
    return tx


# ---- net movement --------------------------------------------------------
def confirmed_net(db: Session, user_id: int, from_date: date, to_date: date) -> Decimal:
    """Money that actually moved between two dates (inclusive): income
    received minus expenses paid. Feeding this into the cash flow keeps a
    period from counting the same payment twice."""

    income = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.direction == "income",
            Transaction.status == "received",
            Transaction.transaction_date >= from_date,
            Transaction.transaction_date <= to_date,
        )
    )
    expenses = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.user_id == user_id,
            Transaction.direction == "expense",
            Transaction.status == "received",
            Transaction.transaction_date >= from_date,
            Transaction.transaction_date <= to_date,
        )
    )
    return Decimal(income or 0) - Decimal(expenses or 0)
