"""Cash-flow timeline: "until next payment" and "monthly" views.

Money is `Decimal` throughout. A view is one pass over dated events, each
carrying the running balance, so the client only formats.

How the numbers stay honest:
- The onboarding "available now" is the balance as of *today*. A view that
  ends today therefore needs no starting figure, and no events. A view that
  extends forward starts from that balance and adds only events from today
  onwards, so already-confirmed money is never counted twice.
- Expected income and unpaid commitments appear as *pending* events until
  confirmed. Confirming one marks the original record used (see
  transaction_service), so it drops out here instead of being counted again.
- A past period walks back from today's balance through confirmed
  transactions; pending income is only shown if it is still unconfirmed,
  i.e. it genuinely has not arrived.
- The savings plan is a plan: it lowers the projected balance, moves no money
  and is labelled as such.
"""

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.expected_income import ExpectedIncome
from app.models.financial_balance import FinancialBalance
from app.models.financial_commitment import FinancialCommitment
from app.models.financial_profile import FinancialProfile
from app.models.transaction import Transaction
from app.schemas.cashflow import CashFlowEvent, CashFlowSummary, View
from app.services import recurrence
from app.services.transaction_service import confirmed_net

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


class RangeError(ValueError):
    pass


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT)


def _month_end(day: date) -> date:
    return date(day.year, day.month, monthrange(day.year, day.month)[1])


def _month_start(month: str | None, today: date) -> date:
    if not month:
        return today.replace(day=1)
    try:
        year, mon = (int(part) for part in month.split("-"))
        return date(year, mon, 1)
    except (ValueError, TypeError):
        raise RangeError("month must look like 2025-06") from None


def _period_label(start: date, end: date, today: date) -> str:
    if start == today:
        return f"Today – {end.day} {end:%b %Y}"
    if start.day == 1 and end == _month_end(start):
        return f"{start:%B %Y}"
    return f"{start.day} {start:%b} – {end.day} {end:%b %Y}"


def _anchor_label(day: date, today: date, is_start: bool) -> str:
    if day == today:
        return "Available now"
    return "Starting balance" if is_start else "Ending balance"


def _context(db: Session, user_id: int):
    profile = db.scalar(
        select(FinancialProfile).where(FinancialProfile.user_id == user_id)
    )
    balance = db.scalar(
        select(FinancialBalance).where(FinancialBalance.user_id == user_id)
    )
    currency = (profile.currency if profile else None) or "ZAR"
    available = _money(balance.available_balance if balance else 0)
    savings_plan = _money(profile.savings_plan_amount if profile else 0)
    return currency, available, savings_plan


def _period(db: Session, user_id: int, view: View, month: str | None, today: date):
    if view == "monthly":
        start = _month_start(month, today)
        return start, _month_end(start)

    upcoming = None
    if not month:
        upcoming = db.scalar(
            select(ExpectedIncome)
            .where(
                ExpectedIncome.user_id == user_id,
                ExpectedIncome.status == "expected",
                ExpectedIncome.expected_date >= today,
            )
            .order_by(ExpectedIncome.expected_date, ExpectedIncome.id)
            .limit(1)
        )
    if upcoming is not None:
        return today, upcoming.expected_date
    # No expected income ahead: show the rest of this month.
    return today, _month_end(today)


def _pending_events(db: Session, user_id: int, start: date, end: date):
    for income in db.scalars(
        select(ExpectedIncome).where(
            ExpectedIncome.user_id == user_id,
            ExpectedIncome.status == "expected",
            ExpectedIncome.expected_date >= start,
            ExpectedIncome.expected_date <= end,
        )
    ):
        yield CashFlowEvent(
            date=income.expected_date,
            label=income.source,
            kind="income",
            amount=_money(income.amount),
            balance=ZERO,
            confirmed=False,
            pending=True,
            note="Depends on payment arriving",
        )

    for commitment in db.scalars(
        select(FinancialCommitment).where(
            FinancialCommitment.user_id == user_id,
            FinancialCommitment.is_paid.is_(False),
            FinancialCommitment.due_date.is_not(None),
            FinancialCommitment.due_date >= start,
            FinancialCommitment.due_date <= end,
        )
    ):
        yield CashFlowEvent(
            date=commitment.due_date,
            label=commitment.name,
            kind="expense",
            amount=_money(commitment.amount),
            balance=ZERO,
            confirmed=False,
            pending=True,
            note="Upcoming",
        )


def _transaction_events(
    db: Session, user_id: int, start: date, end: date, today: date
):
    """Confirmed and expected transactions, with recurring series expanded
    into the future. The stored row itself is skipped when it is before
    `start` (a series that began earlier)."""

    rows = list(
        db.scalars(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.status != "cancelled",
                Transaction.transaction_date <= end,
            )
            .order_by(Transaction.transaction_date, Transaction.id)
        )
    )

    for tx in rows:
        kind = "income" if tx.direction == "income" else "expense"
        confirmed = tx.status == "received"

        # Confirmed today is already inside today's available balance; only
        # confirmed rows from tomorrow onwards are still to come. Savings
        # contributions are the exception: they reduce the balance the
        # moment they are dated, so they always show in their period.
        if confirmed and tx.transaction_date <= today and not tx.is_savings_allocation:
            continue

        if tx.transaction_date >= start:
            yield CashFlowEvent(
                date=tx.transaction_date,
                label=tx.description,
                kind=kind,
                amount=_money(tx.amount),
                balance=ZERO,
                confirmed=confirmed,
                pending=not confirmed,
                note="Confirmed" if confirmed else "Not yet confirmed",
                transaction_id=tx.id,
            )

        # Only unconfirmed series produce future occurrences.
        if tx.recurrence == "none" or confirmed:
            continue
        first_after = max(start, tx.transaction_date + timedelta(days=1))
        for day in recurrence.occurrences_between(tx, first_after, end):
            yield CashFlowEvent(
                date=day,
                label=tx.description,
                kind=kind,
                amount=_money(tx.amount),
                balance=ZERO,
                confirmed=False,
                pending=True,
                note="Repeats",
                transaction_id=tx.id,
            )


def _starting_balance(
    db: Session, user_id: int, start: date, today: date, available: Decimal
) -> Decimal:
    """Today's available balance, rolled back to the start of the period."""

    if start >= today:
        return available
    confirmed_since_start = confirmed_net(db, user_id, start, today - timedelta(days=1))
    return available - confirmed_since_start


def _sort_key(event: CashFlowEvent):
    # Same-day order: expenses before income, so the day never dips below
    # what it really reached.
    order = {"expense": 0, "income": 1, "savings_allocation": 2}
    return (event.date, order.get(event.kind, 1), event.label, event.transaction_id or 0)


def build_timeline(
    db: Session,
    user_id: int,
    view: View = "until_next_payment",
    month: str | None = None,
    today: date | None = None,
) -> CashFlowSummary:
    today = today or date.today()
    currency, available, savings_plan = _context(db, user_id)

    start, end = _period(db, user_id, view, month, today)
    if end < start:
        raise RangeError("Period ends before it starts")

    with_savings = view == "monthly"
    starting = _starting_balance(db, user_id, start, today, available)

    events = list(_transaction_events(db, user_id, start, end, today))
    events += list(_pending_events(db, user_id, start, end))
    if with_savings and savings_plan > ZERO:
        events.append(
            CashFlowEvent(
                date=_month_end(end),
                label="Planned savings allocation",
                kind="savings_allocation",
                amount=savings_plan,
                balance=ZERO,
                confirmed=False,
                pending=False,
                note="A plan, not a transfer",
            )
        )
    events.sort(key=_sort_key)

    timeline = [
        CashFlowEvent(
            date=start,
            label=_anchor_label(start, today, True),
            kind="starting_balance",
            balance=starting,
            confirmed=True,
        )
    ]

    running = starting
    expected_not_received = ZERO
    for event in events:
        if event.kind == "income":
            running += event.amount
            if not event.confirmed:
                expected_not_received += event.amount
        else:
            running -= event.amount
        event.balance = running
        timeline.append(event)

    return CashFlowSummary(
        view=view,
        currency=currency,
        period_label=_period_label(start, end, today),
        start_date=start,
        end_date=end,
        starting_balance=starting,
        projected_end_balance=running,
        expected_not_received=expected_not_received,
        planned_savings=savings_plan if with_savings else ZERO,
        projected_end_label=_anchor_label(end, today, False),
        events=timeline,
    )
