"""Savings goals: one active goal, any number of planned ones.

FlowShelter never moves money. `saved_amount` only changes when the user
says they put money aside (POST .../contributions), and every contribution is
also recorded as a transaction so the Transactions screen tells the same
story as the Goals screen.
"""

from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.savings_goal import SavingsGoal
from app.models.transaction import Transaction
from app.schemas.goal import ContributionIn, GoalIn, GoalOut, GoalUpdate
from app.services.transaction_service import ConflictError, NotFoundError

ZERO = Decimal("0.00")
CENT = Decimal("0.01")
ON_TRACK_GRACE_DAYS = 7


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(CENT)


def _progress(saved: Decimal, target: Decimal) -> int:
    if target <= 0:
        return 0
    value = (saved / target * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return max(0, min(100, int(value)))


def _status(goal: SavingsGoal, today: date) -> tuple[str, str]:
    target = _money(goal.target_amount)
    saved = _money(goal.saved_amount)
    if target > 0 and saved >= target:
        return "reached", "Reached"
    if goal.target_date is None:
        return "no_date", "No date set"

    days_left = (goal.target_date - today).days
    if days_left < 0:
        return "behind", "Past due"

    # Linear pace: by now the user should have saved the share of time that
    # has passed since the goal was created.
    start = goal.created_at.date() if goal.created_at else today
    total_days = max((goal.target_date - start).days, 1)
    expected = target * Decimal(max(total_days - days_left, 0)) / Decimal(total_days)
    if saved + Decimal("0.005") >= expected * Decimal("0.9"):
        return "on_track", "On track"
    if days_left <= ON_TRACK_GRACE_DAYS and saved <= ZERO:
        return "behind", "Behind"
    return "behind", "Behind"


def _to_out(goal: SavingsGoal, today: date) -> GoalOut:
    saved = _money(goal.saved_amount)
    target = _money(goal.target_amount)
    status, label = _status(goal, today)
    return GoalOut(
        id=goal.id,
        name=goal.name,
        target_amount=target,
        saved_amount=saved,
        remaining=max(target - saved, ZERO),
        target_date=goal.target_date,
        priority=goal.priority,
        is_active=goal.is_active,
        progress_percentage=_progress(saved, target),
        status=status,
        status_label=label,
    )


def _get_owned(db: Session, user_id: int, goal_id: int) -> SavingsGoal:
    goal = db.scalar(
        select(SavingsGoal).where(
            SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id
        )
    )
    if goal is None:
        raise NotFoundError(goal_id)
    return goal


def _make_active(db: Session, user_id: int, goal: SavingsGoal) -> None:
    for other in db.scalars(
        select(SavingsGoal).where(
            SavingsGoal.user_id == user_id,
            SavingsGoal.id != goal.id,
            SavingsGoal.is_active.is_(True),
        )
    ):
        other.is_active = False
    goal.is_active = True


def list_goals(db: Session, user_id: int, today: date | None = None) -> list[GoalOut]:
    today = today or date.today()
    goals = db.scalars(
        select(SavingsGoal)
        .where(SavingsGoal.user_id == user_id)
        .order_by(SavingsGoal.is_active.desc(), SavingsGoal.id)
    )
    return [_to_out(goal, today) for goal in goals]


def get_goal(
    db: Session, user_id: int, goal_id: int, today: date | None = None
) -> GoalOut:
    return _to_out(_get_owned(db, user_id, goal_id), today or date.today())


def create_goal(db: Session, user_id: int, data: GoalIn) -> GoalOut:
    goal = SavingsGoal(user_id=user_id, **data.model_dump())
    db.add(goal)
    db.flush()

    # The first goal, or an explicit request, becomes the active one.
    already_active = db.scalar(
        select(SavingsGoal.id).where(
            SavingsGoal.user_id == user_id,
            SavingsGoal.is_active.is_(True),
        )
    )
    if already_active is None:
        goal.is_active = True

    db.commit()
    db.refresh(goal)
    return _to_out(goal, date.today())


def update_goal(
    db: Session, user_id: int, goal_id: int, patch: GoalUpdate
) -> GoalOut:
    goal = _get_owned(db, user_id, goal_id)
    changes = patch.model_dump(exclude_unset=True)

    if changes.get("is_active"):
        _make_active(db, user_id, goal)
    elif "is_active" in changes:
        # Deactivating without picking a replacement is ambiguous; treat it
        # as a no-op so the screen always has one active goal.
        changes.pop("is_active")

    for field, value in changes.items():
        setattr(goal, field, value)

    db.commit()
    db.refresh(goal)
    return _to_out(goal, date.today())


def delete_goal(db: Session, user_id: int, goal_id: int) -> None:
    goal = _get_owned(db, user_id, goal_id)
    was_active = goal.is_active
    db.delete(goal)
    db.flush()

    if was_active:
        # Promote the oldest planned goal so "active goal" is never empty
        # while goals exist.
        next_goal = db.scalar(
            select(SavingsGoal)
            .where(SavingsGoal.user_id == user_id, SavingsGoal.id != goal_id)
            .order_by(SavingsGoal.id)
            .limit(1)
        )
        if next_goal is not None:
            next_goal.is_active = True

    db.commit()


def add_contribution(
    db: Session, user_id: int, goal_id: int, data: ContributionIn
) -> GoalOut:
    goal = _get_owned(db, user_id, goal_id)

    when = data.contributed_on or date.today()
    if when > date.today():
        raise ConflictError("A contribution cannot be dated in the future.")

    goal.saved_amount = _money(goal.saved_amount) + _money(data.amount)
    db.add(
        Transaction(
            user_id=user_id,
            direction="expense",
            description=f"Savings — {goal.name}",
            amount=_money(data.amount),
            transaction_date=when,
            status="received",
            category="savings",
            is_savings_allocation=True,
            confirmed_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    db.refresh(goal)
    return _to_out(goal, date.today())
