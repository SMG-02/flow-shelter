from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.onboarding import Money


class DashboardUser(BaseModel):
    name: str


class ExpectedPayment(BaseModel):
    source: str
    amount: Money
    expected_date: date
    status: str


class SavingsGoalProgress(BaseModel):
    id: int
    name: str
    target_amount: Money
    saved_amount: Money
    progress_percentage: int


class UpcomingCommitment(BaseModel):
    name: str
    amount: Money
    due_date: date


class UpcomingCommitments(BaseModel):
    commitments: list[UpcomingCommitment]
    total: Money


class DashboardAlert(BaseModel):
    type: str
    severity: str
    message: str


class DashboardOverview(BaseModel):
    user: DashboardUser
    currency: str
    available_now: Money
    projected_balance: Money
    essential_commitments: Money
    next_expected_payment: ExpectedPayment | None
    savings_goals: list[SavingsGoalProgress]
    alerts: list[DashboardAlert]
    forecast_is_estimate: bool
