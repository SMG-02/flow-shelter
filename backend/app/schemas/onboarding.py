from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

# Money is serialised as a string ("18450.00") so clients never lose precision.
# Pydantic v2 serialises Decimal as a string by default; the annotation makes
# that explicit in the OpenAPI schema too.
Money = Annotated[
    Decimal,
    Field(max_digits=18, decimal_places=2),
    # Emit as "12000.00"; requests may send either a string or a number.
    PlainSerializer(lambda v: str(v), return_type=str),
]


class FinancialProfileIn(BaseModel):
    work_type: Optional[str] = Field(default=None, max_length=100)
    income_pattern: Optional[Literal["fixed", "irregular", "mixed"]] = None
    typical_income: Optional[Money] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    # Planned monthly saving shown in the monthly cash flow. A plan only.
    savings_plan_amount: Optional[Money] = Field(default=None, ge=0)


class FinancialProfileOut(FinancialProfileIn):
    model_config = ConfigDict(from_attributes=True)


class FinancialBalanceIn(BaseModel):
    available_balance: Optional[Money] = Field(default=None, ge=0)
    existing_savings: Optional[Money] = Field(default=None, ge=0)


class FinancialBalanceOut(FinancialBalanceIn):
    model_config = ConfigDict(from_attributes=True)


class ExpectedIncomeIn(BaseModel):
    """A new expected payment. Always starts with status 'expected'."""

    source: str = Field(min_length=1, max_length=150)
    amount: Money = Field(gt=0)
    expected_date: date


class ExpectedIncomeOut(ExpectedIncomeIn):
    id: int
    status: Literal["expected", "received", "cancelled"]

    model_config = ConfigDict(from_attributes=True)


class SavingsGoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: Money = Field(gt=0)
    saved_amount: Money = Field(default=Decimal("0.00"), ge=0)
    target_date: Optional[date] = None
    priority: Literal["low", "medium", "high"] = "medium"


class SavingsGoalOut(SavingsGoalIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CommitmentIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    amount: Money = Field(gt=0)
    due_date: Optional[date] = None
    is_paid: bool = False


class CommitmentOut(CommitmentIn):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CommitmentsUpdate(BaseModel):
    """Replaces the user's full list of essential commitments."""

    commitments: list[CommitmentIn]


class OnboardingPatch(BaseModel):
    """Partial draft. Only the sections present are written; collections are
    replaced. `current_step` is not accepted here — use
    PUT /api/onboarding/step."""

    financial_profile: Optional[FinancialProfileIn] = None
    financial_balance: Optional[FinancialBalanceIn] = None
    expected_incomes: Optional[list[ExpectedIncomeIn]] = None
    savings_goals: Optional[list[SavingsGoalIn]] = None


class OnboardingStepUpdate(BaseModel):
    current_step: int = Field(ge=1, le=5)


class OnboardingDraft(BaseModel):
    current_step: int
    is_complete: bool
    financial_profile: Optional[FinancialProfileOut] = None
    financial_balance: Optional[FinancialBalanceOut] = None
    expected_incomes: list[ExpectedIncomeOut] = []
    savings_goals: list[SavingsGoalOut] = []
    updated_at: datetime
