"""Onboarding read/write logic.

Every query is scoped by `user_id`; the caller must pass the id from the
validated token, never a client-supplied value.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.expected_income import ExpectedIncome
from app.models.financial_balance import FinancialBalance
from app.models.financial_commitment import FinancialCommitment
from app.models.financial_profile import FinancialProfile
from app.models.onboarding_progress import OnboardingProgress
from app.models.savings_goal import SavingsGoal
from app.schemas.onboarding import OnboardingDraft, OnboardingPatch


class OnboardingIncompleteError(Exception):
    """Raised when completion is requested before all steps have data."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Onboarding incomplete: {', '.join(missing)}")


def get_or_create_progress(db: Session, user_id: int) -> OnboardingProgress:
    progress = db.scalar(
        select(OnboardingProgress).where(OnboardingProgress.user_id == user_id)
    )
    if progress is None:
        progress = OnboardingProgress(user_id=user_id)
        db.add(progress)
        db.flush()
    return progress


def _get_or_create(db: Session, model, user_id: int):
    row = db.scalar(select(model).where(model.user_id == user_id))
    if row is None:
        row = model(user_id=user_id)
        db.add(row)
        db.flush()
    return row


def _apply(row, data) -> None:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(row, field, value)


def save_draft(db: Session, user_id: int, patch: OnboardingPatch) -> OnboardingProgress:
    """Write only the sections present in `patch`.

    `financial_profile` / `financial_balance` are upserts (one row each).
    `expected_incomes` / `savings_goals`, when present, replace the user's
    entire collection — a retried request therefore cannot duplicate entries.
    """

    progress = get_or_create_progress(db, user_id)

    if patch.financial_profile is not None:
        _apply(
            _get_or_create(db, FinancialProfile, user_id),
            patch.financial_profile,
        )

    if patch.financial_balance is not None:
        _apply(
            _get_or_create(db, FinancialBalance, user_id),
            patch.financial_balance,
        )

    if patch.expected_incomes is not None:
        db.execute(
            delete(ExpectedIncome).where(ExpectedIncome.user_id == user_id)
        )
        db.add_all(
            ExpectedIncome(
                user_id=user_id,
                source=item.source,
                amount=item.amount,
                expected_date=item.expected_date,
                status="expected",
            )
            for item in patch.expected_incomes
        )

    if patch.savings_goals is not None:
        db.execute(delete(SavingsGoal).where(SavingsGoal.user_id == user_id))
        db.add_all(
            SavingsGoal(
                user_id=user_id,
                name=item.name,
                target_amount=item.target_amount,
                saved_amount=item.saved_amount,
                target_date=item.target_date,
                priority=item.priority,
            )
            for item in patch.savings_goals
        )

    db.commit()
    db.refresh(progress)
    return progress


def update_step(db: Session, user_id: int, current_step: int) -> OnboardingProgress:
    progress = get_or_create_progress(db, user_id)
    progress.current_step = current_step
    db.commit()
    db.refresh(progress)
    return progress


def get_draft(db: Session, user_id: int) -> OnboardingDraft:
    progress = get_or_create_progress(db, user_id)
    db.commit()

    return OnboardingDraft(
        current_step=progress.current_step,
        is_complete=progress.is_complete,
        financial_profile=db.scalar(
            select(FinancialProfile).where(FinancialProfile.user_id == user_id)
        ),
        financial_balance=db.scalar(
            select(FinancialBalance).where(FinancialBalance.user_id == user_id)
        ),
        expected_incomes=list(
            db.scalars(
                select(ExpectedIncome)
                .where(ExpectedIncome.user_id == user_id)
                .order_by(ExpectedIncome.expected_date, ExpectedIncome.id)
            )
        ),
        savings_goals=list(
            db.scalars(
                select(SavingsGoal)
                .where(SavingsGoal.user_id == user_id)
                .order_by(SavingsGoal.id)
            )
        ),
        updated_at=progress.updated_at,
    )


def complete(db: Session, user_id: int) -> OnboardingProgress:
    """Validate the minimum data set, then mark onboarding complete.

    Step 1 needs a currency (the dashboard is meaningless without one);
    step 2 needs an available balance. Steps 3-5 are optional: a new
    freelancer may have no expected income or savings goal yet.
    """

    profile = db.scalar(
        select(FinancialProfile).where(FinancialProfile.user_id == user_id)
    )
    balance = db.scalar(
        select(FinancialBalance).where(FinancialBalance.user_id == user_id)
    )

    missing = []
    if profile is None or profile.currency is None:
        missing.append("financial_profile.currency")
    if balance is None or balance.available_balance is None:
        missing.append("financial_balance.available_balance")

    if missing:
        raise OnboardingIncompleteError(missing)

    progress = get_or_create_progress(db, user_id)
    progress.is_complete = True
    progress.current_step = 5
    progress.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(progress)
    return progress


def list_commitments(db: Session, user_id: int) -> list[FinancialCommitment]:
    return list(
        db.scalars(
            select(FinancialCommitment)
            .where(FinancialCommitment.user_id == user_id)
            .order_by(
                FinancialCommitment.due_date.asc().nulls_last(),
                FinancialCommitment.id,
            )
        )
    )


def replace_commitments(db: Session, user_id: int, items) -> list[FinancialCommitment]:
    """Replace the user's commitments in one transaction (retry-safe)."""
    db.execute(
        delete(FinancialCommitment).where(FinancialCommitment.user_id == user_id)
    )
    db.add_all(
        FinancialCommitment(
            user_id=user_id,
            name=item.name,
            amount=item.amount,
            due_date=item.due_date,
            is_paid=item.is_paid,
        )
        for item in items
    )
    db.commit()
    return list_commitments(db, user_id)
