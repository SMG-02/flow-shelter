from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.onboarding import Money

View = Literal["until_next_payment", "monthly"]

# Every row on the timeline carries a running balance, including the savings
# plan, so a client renders them all the same way.
EventKind = Literal[
    "starting_balance",
    "income",
    "expense",
    "savings_allocation",
]


class CashFlowEvent(BaseModel):
    date: date
    label: str
    kind: EventKind
    # Present on money movements; the plan changes no real money.
    amount: Money | None = None
    # Balance after this event.
    balance: Money
    confirmed: bool = Field(
        description="True when the money has actually moved; False when expected."
    )
    pending: bool = Field(
        default=False,
        description="True for items the user still has to confirm (expected "
        "income not yet received, unpaid commitments).",
    )
    note: str | None = None
    transaction_id: int | None = None


class CashFlowSummary(BaseModel):
    view: View
    currency: str
    period_label: str = Field(
        description="Display title, e.g. 'Today – 28 Jun 2025' or 'June 2025'."
    )
    start_date: date
    end_date: date
    starting_balance: Money
    projected_end_balance: Money
    projected_end_label: str = Field(
        description="Card title for the end figure, e.g. 'Projected end balance'."
    )
    expected_not_received: Money = Field(
        description="Expected income inside the period that has not arrived."
    )
    planned_savings: Money = Field(
        description="Monthly savings plan applied to this period (0 when none)."
    )
    events: list[CashFlowEvent]
