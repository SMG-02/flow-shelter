from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.cashflow import CashFlowSummary
from app.services import cashflow_service

router = APIRouter(prefix="/cashflow", tags=["Cash flow"])


@router.get("/timeline", response_model=CashFlowSummary)
def get_timeline(
    view: Literal["until_next_payment", "monthly"] = Query(
        "until_next_payment",
        description="'until_next_payment' runs from today to the next "
        "expected payment; 'monthly' covers one calendar month.",
    ),
    month: str | None = Query(
        None,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Month for the monthly view, e.g. 2025-06. Defaults to "
        "the current month.",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dated events with a running balance, plus starting and projected
    end balances. Figures are estimates; expected money is not guaranteed."""
    try:
        return cashflow_service.build_timeline(
            db, current_user.id, view=view, month=month
        )
    except cashflow_service.RangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
