from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

TRANSACTION_DIRECTIONS = ("income", "expense")
# 'received' covers both directions: income received and expense paid.
TRANSACTION_STATUSES = ("expected", "received", "cancelled")

# "Mark received" / "Mark paid" only makes sense before the money has moved.
OPEN_STATUSES = ("expected",)


class Transaction(Base, TimestampMixin):
    """A movement of money: money in (income) or out (expense).

    A transaction is first recorded with status 'expected' — the money has
    not moved yet — and the cash-flow projection may include it. Once it is
    'received' (income) or the payment is made (expense, also 'received'), it
    counts as real money and is included in the confirmed balance instead.
    'cancelled' rows never count.

    `source_income_id` / `source_commitment_id` link a confirmed row back to
    the onboarding record it was created from, so the same payment is never
    counted twice (the income/commitment is marked used and drops out of the
    forecast).
    """

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('income', 'expense')",
            name="ck_transactions_direction",
        ),
        CheckConstraint(
            "status IN ('expected', 'received', 'cancelled')",
            name="ck_transactions_status",
        ),
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str] = mapped_column(String(150), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    transaction_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="expected", server_default="expected"
    )
    category: Mapped[str | None] = mapped_column(String(50))
    recurrence: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none", server_default="none"
    )
    recurrence_interval: Mapped[int | None] = mapped_column(Integer)
    # Last date a recurring series may generate; also lets the scheduler know
    # the series is over.
    recurrence_end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_savings_allocation: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    source_income_id: Mapped[int | None] = mapped_column(
        ForeignKey("expected_incomes.id", ondelete="SET NULL"), index=True
    )
    source_commitment_id: Mapped[int | None] = mapped_column(
        ForeignKey("financial_commitments.id", ondelete="SET NULL"), index=True
    )
