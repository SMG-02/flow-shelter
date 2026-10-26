"""Dashboard calculations and financial alerts.

All money is `Decimal`. Every query is scoped to `user_id`.

Forecast horizon: `settings.FORECAST_HORIZON_DAYS` from today. The same cutoff
is applied to expected income and unpaid commitments so the projection never
mixes time windows.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.expected_income import ExpectedIncome
from app.models.financial_balance import FinancialBalance
from app.models.financial_commitment import FinancialCommitment
from app.models.financial_profile import FinancialProfile
from app.models.savings_goal import SavingsGoal
from app.models.user import User
from app.schemas.dashboard import (
    DashboardAlert,
    DashboardOverview,
    DashboardUser,
    ExpectedPayment,
    SavingsGoalProgress,
    UpcomingCommitment,
    UpcomingCommitments,
)

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _money(value) -> Decimal:
    return (Decimal(value) if value is not None else ZERO).quantize(CENT)


def _percent(part: Decimal, whole: Decimal) -> int:
    if whole <= 0:
        return 0
    return min(
        100,
        int((part / whole * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
    )


def _window(today: date) -> tuple[date, date]:
    horizon = today + timedelta(days=settings.FORECAST_HORIZON_DAYS)
    return today, horizon


def _alerts(
    *,
    today: date,
    currency: str,
    profile: FinancialProfile | None,
    available: Decimal,
    commitments_total: Decimal,
    next_payment: ExpectedIncome | None,
    goals: list[SavingsGoal],
    has_large_commitments: bool,
) -> list[DashboardAlert]:
    """Alert rules, ordered most urgent first."""

    alerts: list[DashboardAlert] = []

    if profile is None or profile.currency is None:
        alerts.append(
            DashboardAlert(
                type="profile_incomplete",
                severity="info",
                message="Finish onboarding to get accurate forecasts.",
            )
        )

    committed = _money(commitments_total)
    if has_large_commitments and committed > ZERO and available < committed:
        alerts.append(
            DashboardAlert(
                type="commitments_exceed_balance",
                severity="urgent",
                message=(
                    f"Your commitments ({currency} {committed}) are more "
                    f"than what you have available ({currency} {available})."
                ),
            )
        )

    if next_payment is not None and next_payment.status == "expected":
        overdue = next_payment.expected_date < today
        alerts.append(
            DashboardAlert(
                type="payment_overdue" if overdue else "payment_expected",
                severity="warning" if overdue else "info",
                message=(
                    f"{next_payment.source} payment was due on "
                    f"{next_payment.expected_date:%d %b %Y} but has not arrived."
                    if overdue
                    else f"{next_payment.source} payment is still expected "
                    f"on {next_payment.expected_date:%d %b %Y}."
                ),
            )
        )

    for goal in goals:
        target = _money(goal.target_amount)
        saved = _money(goal.saved_amount)
        if target > 0 and saved >= target:
            alerts.append(
                DashboardAlert(
                    type="goal_reached",
                    severity="success",
                    message=f"You reached your '{goal.name}' goal.",
                )
            )
        elif saved <= 0 and goal.target_date is not None:
            days_left = (goal.target_date - today).days
            if 0 <= days_left <= 14:
                alerts.append(
                    DashboardAlert(
                        type="goal_due_soon",
                        severity="warning",
                        message=(
                            f"'{goal.name}' is due in {days_left} day(s) "
                            "and nothing has been saved yet."
                        ),
                    )
                )

    if available == ZERO:
        alerts.append(
            DashboardAlert(
                type="no_available_balance",
                severity="info",
                message="Add what you have available so projections are accurate.",
            )
        )

    return alerts


def build_dashboard_overview(db: Session, user_id: int) -> DashboardOverview:
    today = date.today()
    window_start, window_end = _window(today)

    user = db.get(User, user_id)
    profile = db.scalar(
        select(FinancialProfile).where(FinancialProfile.user_id == user_id)
    )
    balance = db.scalar(
        select(FinancialBalance).where(FinancialBalance.user_id == user_id)
    )
    currency = profile.currency if profile and profile.currency else "ZAR"
    available = _money(balance.available_balance) if balance else ZERO

    next_payment = db.scalar(
        select(ExpectedIncome)
        .where(
            ExpectedIncome.user_id == user_id,
            ExpectedIncome.status == "expected",
            ExpectedIncome.expected_date >= window_start,
            ExpectedIncome.expected_date <= window_end,
        )
        .order_by(ExpectedIncome.expected_date, ExpectedIncome.id)
        .limit(1)
    )

    expected_income_total = _money(
        db.scalar(
            select(func.coalesce(func.sum(ExpectedIncome.amount), 0)).where(
                ExpectedIncome.user_id == user_id,
                ExpectedIncome.status == "expected",
                ExpectedIncome.expected_date >= window_start,
                ExpectedIncome.expected_date <= window_end,
            )
        )
    )

    commitments_total = _money(
        db.scalar(
            select(func.coalesce(func.sum(FinancialCommitment.amount), 0)).where(
                FinancialCommitment.user_id == user_id,
                FinancialCommitment.is_paid.is_(False),
                FinancialCommitment.due_date.is_not(None),
                FinancialCommitment.due_date >= window_start,
                FinancialCommitment.due_date <= window_end,
            )
        )
    )

    goals = list(
        db.scalars(
            select(SavingsGoal)
            .where(SavingsGoal.user_id == user_id)
            .order_by(SavingsGoal.id)
        )
    )

    projected = available + expected_income_total - commitments_total

    return DashboardOverview(
        user=DashboardUser(name=user.name.split(" ")[0] if user else ""),
        currency=currency,
        available_now=available,
        projected_balance=projected,
        essential_commitments=commitments_total,
        next_expected_payment=(
            ExpectedPayment(
                source=next_payment.source,
                amount=_money(next_payment.amount),
                expected_date=next_payment.expected_date,
                status=next_payment.status,
            )
            if next_payment
            else None
        ),
        savings_goals=[
            SavingsGoalProgress(
                id=goal.id,
                name=goal.name,
                target_amount=_money(goal.target_amount),
                saved_amount=_money(goal.saved_amount),
                progress_percentage=_percent(
                    _money(goal.saved_amount), _money(goal.target_amount)
                ),
            )
            for goal in goals
        ],
        alerts=_alerts(
            today=today,
            currency=currency,
            profile=profile,
            available=available,
            commitments_total=commitments_total,
            next_payment=next_payment,
            goals=goals,
            has_large_commitments=commitments_total > 0,
        ),
        forecast_is_estimate=True,
    )


def build_alerts(db: Session, user_id: int) -> list[DashboardAlert]:
    return build_dashboard_overview(db, user_id).alerts


def build_upcoming(db: Session, user_id: int) -> UpcomingCommitments:
    """Unpaid commitments due inside the forecast horizon, soonest first."""

    today = date.today()
    _, window_end = _window(today)

    rows = list(
        db.scalars(
            select(FinancialCommitment)
            .where(
                FinancialCommitment.user_id == user_id,
                FinancialCommitment.is_paid.is_(False),
                FinancialCommitment.due_date.is_not(None),
                FinancialCommitment.due_date >= today,
                FinancialCommitment.due_date <= window_end,
            )
            .order_by(FinancialCommitment.due_date, FinancialCommitment.id)
        )
    )

    total = sum((_money(row.amount) for row in rows), ZERO)
    return UpcomingCommitments(
        commitments=[
            UpcomingCommitment(
                name=row.name,
                amount=_money(row.amount),
                due_date=row.due_date,
            )
            for row in rows
        ],
        total=total,
    )
