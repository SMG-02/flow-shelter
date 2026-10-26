from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

SAVINGS_GOAL_PRIORITIES = ("low", "medium", "high")


class SavingsGoal(Base, TimestampMixin):
    """A savings goal — onboarding step 4."""

    __tablename__ = "savings_goals"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_savings_goals_priority",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    saved_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=0, server_default="0"
    )
    target_date: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium", server_default="medium"
    )
    # Exactly one goal may be "active" at a time; the rest are planned.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
