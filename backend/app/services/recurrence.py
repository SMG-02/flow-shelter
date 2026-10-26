"""When a recurring transaction falls on a given date.

Only the stored row's own date matters for the Transactions list. This helper
answers the different question the cash flow asks: "does this series produce
an occurrence on / before this date?".
"""

from calendar import monthrange
from datetime import date, timedelta

from app.models.transaction import Transaction

_UNITS = {
    "daily": 1,
    "weekly": 7,
}


def occurrence_on_or_before(tx: Transaction, day: date) -> date | None:
    """The last occurrence of `tx` on or before `day`, or None if it never
    occurs by then (series starts later, or has ended). A one-off transaction
    counts as a single occurrence on its own date."""

    if day < tx.transaction_date:
        return None
    if tx.recurrence == "none" or not tx.recurrence_interval:
        return tx.transaction_date
    if tx.recurrence_end_date is not None and tx.recurrence_end_date < day:
        day = tx.recurrence_end_date
    if day < tx.transaction_date:
        return None

    if tx.recurrence in _UNITS:
        step = _UNITS[tx.recurrence] * tx.recurrence_interval
        count = (day - tx.transaction_date).days // step
        return tx.transaction_date + timedelta(days=count * step)

    if tx.recurrence == "monthly":
        # Floor division guarantees the shift lands on or before `day`
        # (the day of month is clamped, so it can only come earlier).
        count = _month_diff(tx.transaction_date, day) // tx.recurrence_interval
        return _add_months(tx.transaction_date, count * tx.recurrence_interval)

    if tx.recurrence == "yearly":
        years = day.year - tx.transaction_date.year
        count = years // tx.recurrence_interval
        while count >= 0:
            result = _add_months(tx.transaction_date, count * 12 * tx.recurrence_interval)
            if result is not None and result <= day:
                return result
            count -= 1
        return None

    return None


def next_occurrence(tx: Transaction, after: date) -> date | None:
    """The first occurrence strictly after `after`, or None if the series has
    ended. One-off transactions have no next occurrence."""

    if tx.recurrence == "none" or not tx.recurrence_interval:
        return None

    step = _UNITS.get(tx.recurrence)
    if step is not None:
        step *= tx.recurrence_interval
        day = tx.transaction_date
        if after >= day:
            day += ((after - day).days // step + 1) * step
        else:
            return day
    else:
        stride = tx.recurrence_interval * (12 if tx.recurrence == "yearly" else 1)
        months = _month_diff(tx.transaction_date, after)
        steps = max(months // stride, 0) + 1
        day = _add_months(tx.transaction_date, steps * stride)
        # Day-of-month clamping can pull an occurrence on or before `after`.
        while day is not None and day <= after:
            steps += 1
            day = _add_months(tx.transaction_date, steps * stride)
        if day is None:
            return None

    if tx.recurrence_end_date is not None and day > tx.recurrence_end_date:
        return None
    return day


def occurrences_between(tx: Transaction, start: date, end: date) -> list[date]:
    """Every occurrence of `tx` inside [start, end], in order."""

    first = tx.transaction_date if tx.transaction_date >= start else next_occurrence(
        tx, start - timedelta(days=1)
    )
    found: list[date] = []
    day = first
    while day is not None and day <= end:
        found.append(day)
        day = next_occurrence(tx, day)
    return found


def _month_diff(start: date, end: date) -> int:
    return (end.year - start.year) * 12 + (end.month - start.month)


def _add_months(day: date, months: int) -> date | None:
    """Shift by whole months, clamping to the month's last day (31 Jan + 1
    month -> 28/29 Feb). Returns None when the shift leaves the calendar."""

    index = day.month - 1 + months
    year = day.year + index // 12
    if year < 1 or year > 9999:
        return None
    month = index % 12 + 1

    last = monthrange(year, month)[1]
    return date(year, month, min(day.day, last))
