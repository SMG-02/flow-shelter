from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.goal import ContributionIn, GoalIn, GoalOut, GoalUpdate
from app.services import goal_service as service
from app.services.transaction_service import ConflictError, NotFoundError

router = APIRouter(prefix="/goals", tags=["Goals"])


def _raise_http(exc: Exception):
    if isinstance(exc, NotFoundError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Goal not found")
    raise HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.get("", response_model=list[GoalOut])
def list_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All goals, the active one first, with progress and status label."""
    return service.list_goals(db, current_user.id)


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
def create_goal(
    body: GoalIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a goal. The first goal created becomes the active one."""
    return service.create_goal(db, current_user.id, body)


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_goal(db, current_user.id, goal_id)
    except NotFoundError as exc:
        _raise_http(exc)


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: int,
    body: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Edit a goal. Send `is_active: true` to make it the active goal (the
    previous active goal becomes planned)."""
    try:
        return service.update_goal(db, current_user.id, goal_id, body)
    except NotFoundError as exc:
        _raise_http(exc)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_goal(db, current_user.id, goal_id)
    except NotFoundError as exc:
        _raise_http(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{goal_id}/contributions", response_model=GoalOut)
def add_contribution(
    goal_id: int,
    body: ContributionIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record money the user has actually put aside. FlowShelter moves no
    money; this only updates the amount saved and lists the payment."""
    try:
        return service.add_contribution(db, current_user.id, goal_id, body)
    except (NotFoundError, ConflictError) as exc:
        _raise_http(exc)
