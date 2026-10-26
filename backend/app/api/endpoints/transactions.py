from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.transaction import (
    TransactionIn,
    TransactionOptions,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)
from app.services import transaction_service as service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def _raise_http(exc: Exception):
    if isinstance(exc, service.NotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found")
    raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("/options", response_model=TransactionOptions)
def get_options(current_user: User = Depends(get_current_user)):
    """Allowed values for the form's Status / Category / Recurrence dropdowns."""
    return service.options()


@router.get("", response_model=TransactionPage)
def list_transactions(
    month: str | None = Query(
        None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Month to show as YYYY-MM. Defaults to the current month.",
    ),
    from_date: date | None = Query(
        None, description="'From date (optional)' filter, applied inside the month."
    ),
    kind: Literal["all", "income", "expenses"] = Query("all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """One month of transactions, newest first, with that month's totals."""
    try:
        return service.list_transactions(
            db, current_user.id, month=month, from_date=from_date, kind=kind
        )
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)
        ) from exc


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    body: TransactionIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record an income or expense. 'expected' means the money has not moved
    yet; 'received' means it has (for expenses: paid)."""
    return service.create(db, current_user.id, body)


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get(db, current_user.id, transaction_id)
    except service.NotFoundError as exc:
        _raise_http(exc)


@router.patch("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: int,
    body: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update(db, current_user.id, transaction_id, body)
    except (service.NotFoundError, service.ConflictError) as exc:
        _raise_http(exc)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete(db, current_user.id, transaction_id)
    except (service.NotFoundError, service.ConflictError) as exc:
        _raise_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{transaction_id}/confirm", response_model=TransactionOut)
def confirm_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """'Mark received' (income) / 'Mark paid' (expense). If the transaction
    came from an onboarding income or commitment, that record is closed too."""
    try:
        return service.mark_transaction_received(db, current_user.id, transaction_id)
    except (service.NotFoundError, service.ConflictError) as exc:
        _raise_http(exc)


@router.post("/incomes/{income_id}/mark-received", response_model=TransactionOut)
def mark_income_received(
    income_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm an expected income from onboarding. Creates the matching
    transaction and stops the income being projected."""
    try:
        return service.mark_income_received(db, current_user.id, income_id)
    except (service.NotFoundError, service.ConflictError) as exc:
        _raise_http(exc)


@router.post("/commitments/{commitment_id}/mark-paid", response_model=TransactionOut)
def mark_commitment_paid(
    commitment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """'Mark paid' on an onboarding commitment: records the expense and stops
    the commitment being projected."""
    try:
        return service.mark_commitment_paid(db, current_user.id, commitment_id)
    except (service.NotFoundError, service.ConflictError) as exc:
        _raise_http(exc)
