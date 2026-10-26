from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.onboarding import Money

Status = Literal["on_track", "behind", "reached", "no_date"]


class GoalIn(BaseModel):
    """Create / edit goal form: name, target, amount already saved, date."""

    name: str = Field(min_length=1, max_length=100)
    target_amount: Money = Field(gt=0)
    saved_amount: Money = Field(default=0, ge=0)
    target_date: Optional[date] = None
    priority: Literal["low", "medium", "high"] = "medium"


class GoalUpdate(BaseModel):
    """Partial update. Only the fields sent are written."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    target_amount: Optional[Money] = Field(default=None, gt=0)
    saved_amount: Optional[Money] = Field(default=None, ge=0)
    # Sending null clears the date; omitting it leaves the date alone.
    target_date: Optional[date] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    is_active: Optional[bool] = None


class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: Money
    saved_amount: Money
    remaining: Money
    target_date: Optional[date] = None
    priority: str
    is_active: bool
    progress_percentage: int = Field(ge=0, le=100)
    status: Status
    status_label: str = Field(description="Display text, e.g. 'On track'.")

    model_config = ConfigDict(from_attributes=True)


class ContributionIn(BaseModel):
    """'Add to savings' — records money the user has actually put aside."""

    amount: Money = Field(gt=0)
    contributed_on: Optional[date] = None
