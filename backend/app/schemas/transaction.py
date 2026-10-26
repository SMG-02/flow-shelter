from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.onboarding import Money

Direction = Literal["income", "expense"]
Status = Literal["expected", "received", "cancelled"]

# "Monthly" on the add-transaction form -> a series that repeats every month.
RECURRENCES = ("none", "daily", "weekly", "monthly", "yearly")

INCOME_CATEGORIES = ("client_payment", "salary", "refund", "other")
EXPENSE_CATEGORIES = (
    "housing",
    "utilities",
    "food",
    "transport",
    "subscriptions",
    "equipment",
    "tax",
    "other",
)


class TransactionIn(BaseModel):
    """Create-transaction form: Income/Expense toggle, description, amount,
    date, status, category, recurrence and notes."""

    direction: Direction
    description: str = Field(min_length=1, max_length=150)
    amount: Money = Field(gt=0)
    transaction_date: date
    status: Status = "expected"
    category: Optional[str] = Field(default=None, max_length=50)
    recurrence: Literal["none", "daily", "weekly", "monthly", "yearly"] = "none"
    recurrence_interval: Optional[int] = Field(default=None, ge=1, le=365)
    recurrence_end_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check_recurrence(self):
        if self.recurrence != "none" and self.recurrence_interval is None:
            self.recurrence_interval = 1
        if self.recurrence == "none":
            self.recurrence_interval = None
            self.recurrence_end_date = None
        if (
            self.recurrence_end_date is not None
            and self.recurrence_end_date < self.transaction_date
        ):
            raise ValueError("recurrence_end_date cannot be before transaction_date")
        return self


class TransactionUpdate(BaseModel):
    """Partial update. Only the fields sent are written."""

    direction: Optional[Direction] = None
    description: Optional[str] = Field(default=None, min_length=1, max_length=150)
    amount: Optional[Money] = Field(default=None, gt=0)
    transaction_date: Optional[date] = None
    status: Optional[Status] = None
    category: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)


class TransactionOut(BaseModel):
    id: int
    direction: Direction
    description: str
    amount: Money
    transaction_date: date
    status: Status
    category: Optional[str] = None
    recurrence: str
    recurrence_interval: Optional[int] = None
    recurrence_end_date: Optional[date] = None
    notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    is_savings_allocation: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionPage(BaseModel):
    """One month of the Transactions screen, newest first."""

    items: list[TransactionOut]
    total_income: Money
    total_expenses: Money
    net: Money
    month: str  # "2025-06"


class TransactionOptions(BaseModel):
    """Values for the form's dropdowns, so the app does not hard-code them."""

    statuses: list[str]
    recurrences: list[str]
    income_categories: list[str]
    expense_categories: list[str]

    @classmethod
    def defaults(cls) -> "TransactionOptions":
        return cls(
            statuses=["expected", "received", "cancelled"],
            recurrences=list(RECURRENCES),
            income_categories=list(INCOME_CATEGORIES),
            expense_categories=list(EXPENSE_CATEGORIES),
        )
