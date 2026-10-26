from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    DashboardAlert,
    DashboardOverview,
    UpcomingCommitments,
)
from app.services.dashboard_service import (
    build_alerts,
    build_dashboard_overview,
    build_upcoming,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current financial picture. Figures are estimates, not confirmed cash."""
    return build_dashboard_overview(db, current_user.id)


@router.get("/upcoming", response_model=UpcomingCommitments)
def get_upcoming_commitments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unpaid commitments due within the forecast horizon, soonest first."""
    return build_upcoming(db, current_user.id)


@router.get("/alerts", response_model=list[DashboardAlert])
def get_dashboard_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Financial alerts, most urgent first."""
    return build_alerts(db, current_user.id)
