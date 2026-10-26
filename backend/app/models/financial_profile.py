from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class FinancialProfile(Base, TimestampMixin):
    """Work and income information collected in onboarding step 1."""

    __tablename__ = "financial_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    work_type: Mapped[str | None] = mapped_column(String(100))
    income_pattern: Mapped[str | None] = mapped_column(String(50))
    typical_income: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    # Planned monthly savings. A plan only: nothing is moved or transferred.
    savings_plan_amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        default=0,
        server_default=text("0"),
    )
