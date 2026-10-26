"""Onboarding steps 1-5 (design: mobile/screens/Screenshot *.png).

Each screen:
- paints immediately from the draft the app already loaded,
- saves on Continue (PATCH, then PUT /step), then asks the app for the next
  step,
- saves on "Save & exit" too, then returns to the dashboard.

Existing values are kept if the user leaves a field alone.
"""

from datetime import date
from decimal import Decimal, InvalidOperation

import flet as ft

from api.client import error_message
from theme import (
    BG,
    BORDER,
    INK,
    MUTED,
    NOTE_BG,
    SURFACE,
    format_date,
    money,
    note,
    primary_button,
    secondary_button,
    style_input,
    text_button,
)
from widgets import (
    DateField,
    card,
    error_text,
    labeled,
    nav_footer,
    onboarding_view,
    progress_header,
    set_error,
    step_title,
    top_bar,
)

INCOME_PATTERNS = [
    ft.DropdownOption(key="fixed", text="Fixed"),
    ft.DropdownOption(key="irregular", text="Irregular"),
    ft.DropdownOption(key="mixed", text="Mixed"),
]

CURRENCIES = [
    ft.DropdownOption(key="ZAR", text="ZAR — South African rand"),
    ft.DropdownOption(key="USD", text="USD — US dollar"),
    ft.DropdownOption(key="EUR", text="EUR — Euro"),
    ft.DropdownOption(key="GBP", text="GBP — British pound"),
]

PRIORITIES = [
    ft.DropdownOption(key="low", text="Low"),
    ft.DropdownOption(key="medium", text="Medium"),
    ft.DropdownOption(key="high", text="High"),
]


def _to_amount(raw) -> str | None:
    """'R 18 450' / '18 450,50' / '18450' -> '18450.00' (None when blank).

    Raises ValueError for anything that is not a number, so a typo shows up
    next to the field instead of coming back as a 422.
    """

    if raw is None:
        return None
    cleaned = (
        str(raw)
        .replace("R", "")
        .replace(" ", "")
        .replace(" ", "")
        .replace(",", ".")
        .strip()
    )
    if not cleaned:
        return None
    if cleaned.count(".") > 1:
        raise ValueError(f"“{raw}” is not a valid amount.")
    try:
        return f"{Decimal(cleaned):.2f}"
    except InvalidOperation:
        raise ValueError(f"“{raw}” is not a valid amount.") from None


def _shown_amount(value) -> str:
    """Render an API money string in a text field without '.0' noise."""

    if value in (None, ""):
        return ""
    return _to_amount(value) or ""


class OnboardingScreen:
    """Base class with shared save/exit plumbing."""

    step = 1
    title = ""
    subtitle = None

    def __init__(self, page: ft.Page, app):
        self.page = page
        self.app = app
        self.draft = app.draft or {}
        self.error = error_text()

    # ---- to be implemented by each step ---------------------------------
    def body(self) -> list[ft.Control]:
        raise NotImplementedError

    def payload(self) -> dict:
        return {}

    def footer(self) -> ft.Control:
        return nav_footer(
            on_back=lambda e: self.back(),
            on_continue=lambda e: self.save_and(next_step=self.step + 1),
        )

    # ---- helpers ---------------------------------------------------------
    def back(self):
        if self.step <= 1:
            return
        self.app.show_step(self.step - 1)

    def view(self) -> ft.View:
        return onboarding_view(
            self.page,
            step=self.step,
            title=self.title,
            subtitle=self.subtitle,
            body=[*self.body(), self.error],
            footer=self.footer(),
            on_save_exit=lambda e: self.save_and(exit_on_success=True),
            scroll=True,
        )

    def save_and(self, next_step: int | None = None, exit_on_success=False):
        set_error(self.error, None, self.page)
        self.page.run_task(self._save, next_step, exit_on_success)

    async def _save(self, next_step, exit_on_success):
        try:
            data = self.payload()
            if data is not None:
                await self.app.api.patch_onboarding(**data)
            # The saved step is this screen's own step, so reopening the app
            # resumes here rather than skipping ahead to a screen never shown.
            await self.app.api.set_step(self.step)
        except ValueError as exc:
            set_error(self.error, str(exc), self.page)
            return
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            set_error(self.error, error_message(exc), self.page)
            return
        if exit_on_success:
            await self.app.open_dashboard()
            return
        await self.app.reload_draft()
        self.app.show_step(next_step)


# ---------------------------------------------------------------------------
# Step 1 — Tell us about your work
# ---------------------------------------------------------------------------
class WorkStep(OnboardingScreen):
    step = 1
    title = "Tell us about your work"
    subtitle = (
        "This helps us shape a useful first cash-flow plan. "
        "No client details needed."
    )

    def __init__(self, page, app):
        super().__init__(page, app)
        profile = self.draft.get("financial_profile") or {}

        self.work_type = style_input(
            ft.TextField(label="e.g. Graphic designer", value=profile.get("work_type") or "")
        )
        self.income_pattern = style_input(
            ft.Dropdown(
                value=profile.get("income_pattern") or "irregular",
                options=INCOME_PATTERNS,
            )
        )
        self.typical_income = style_input(
            ft.TextField(
                label="R 0",
                value=_shown_amount(profile.get("typical_income")),
                keyboard_type=ft.KeyboardType.NUMBER,
            )
        )
        self.next_date = DateField(page, "dd/mm/yyyy")
        self.next_amount = style_input(
            ft.TextField(label="R 0", keyboard_type=ft.KeyboardType.NUMBER)
        )
        self.currency = style_input(
            ft.Dropdown(
                value=profile.get("currency") or "ZAR",
                options=CURRENCIES,
            )
        )

    def body(self):
        return [
            labeled("Type of freelance work *", self.work_type),
            labeled("Income pattern", self.income_pattern),
            labeled("Typical income amount (optional)", self.typical_income),
            labeled("Next expected payment date (optional)", self.next_date.field),
            labeled("Next expected payment amount (optional)", self.next_amount),
            labeled("Currency", self.currency),
            ft.Divider(color=BORDER),
        ]

    def payload(self) -> dict:
        if not self.work_type.value.strip():
            raise ValueError("Work type is required.")

        profile = {
            "work_type": self.work_type.value.strip(),
            "income_pattern": self.income_pattern.value,
            "currency": self.currency.value,
        }
        typical = _to_amount(self.typical_income.value)
        if typical is not None:
            profile["typical_income"] = typical

        data: dict = {"financial_profile": profile}

        # The optional next payment becomes an expected-income record, unless
        # the user already has some (so we never duplicate or overwrite them).
        amount = _to_amount(self.next_amount.value)
        if amount and not self.draft.get("expected_incomes"):
            data["expected_incomes"] = [
                {
                    "source": self.work_type.value.strip(),
                    "amount": amount,
                    "expected_date": self.next_date.value
                    or date.today().isoformat(),
                }
            ]
        return data

    def footer(self):
        # Nothing on step 1 is required to leave, so both buttons just move on.
        return nav_footer(
            on_back=lambda e: self.save_and(exit_on_success=True),
            skip_label="Skip optional details",
            on_continue=lambda e: self.save_and(next_step=2),
            continue_label="Continue",
            back_label="Back",
        )


# ---------------------------------------------------------------------------
# Step 2 — What do you have available now?
# ---------------------------------------------------------------------------
class BalanceStep(OnboardingScreen):
    step = 2
    title = "What do you have available now?"
    subtitle = (
        "Only include money you can currently use. "
        "Do not include expected payments."
    )

    def __init__(self, page, app):
        super().__init__(page, app)
        balance = self.draft.get("financial_balance") or {}
        self.available = style_input(
            ft.TextField(
                label="R 0",
                value=_shown_amount(balance.get("available_balance")),
                keyboard_type=ft.KeyboardType.NUMBER,
            )
        )
        self.savings = style_input(
            ft.TextField(
                label="R 0",
                value=_shown_amount(balance.get("existing_savings")),
                keyboard_type=ft.KeyboardType.NUMBER,
            )
        )

    def body(self):
        return [
            labeled("Current available balance *", self.available),
            labeled("Existing savings (optional)", self.savings),
            note(
                "Use money you have right now. Payments you are waiting on "
                "belong on the next step, so they are not counted twice."
            ),
            ft.Divider(color=BORDER),
        ]

    def payload(self) -> dict:
        available = _to_amount(self.available.value)
        if available is None:
            raise ValueError("Available balance is required.")
        data = {"financial_balance": {"available_balance": available}}
        savings = _to_amount(self.savings.value)
        if savings is not None:
            data["financial_balance"]["existing_savings"] = savings
        return data


# ---------------------------------------------------------------------------
# Step 3 — What income are you expecting?
# ---------------------------------------------------------------------------
class IncomeStep(OnboardingScreen):
    step = 3
    title = "What income are you expecting?"
    subtitle = (
        "Expected money is kept separate until you mark it received."
    )

    def __init__(self, page, app):
        super().__init__(page, app)
        existing = self.draft.get("expected_incomes") or []
        self.rows = ft.Column(spacing=12, controls=[])
        for item in existing or [{}]:
            self._add_row(item)
        self.add_button = ft.Button(
            content="+ Add another income",
            color=INK,
            style=ft.ButtonStyle(
                bgcolor=SURFACE,
                side=ft.BorderSide(1, BORDER),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=lambda e: self._add_row({}),
        )

    def _add_row(self, item: dict):
        source = style_input(
            ft.TextField(label="e.g. Mokoena Studio project", value=item.get("source") or "")
        )
        amount = style_input(
            ft.TextField(
                label="R 0",
                value=_shown_amount(item.get("amount")),
                keyboard_type=ft.KeyboardType.NUMBER,
            )
        )
        when = DateField(self.page, "dd/mm/yyyy")
        if item.get("expected_date"):
            when.value = item["expected_date"]

        row = ft.Column(spacing=10)
        row.data = {"source": source, "amount": amount, "date": when}

        def remove(e, r=row):
            self.rows.controls.remove(r)
            self.page.update()

        row.controls = [
            card(
                ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text(
                                    (item.get("source") or "New income"),
                                    size=14,
                                    weight=ft.FontWeight.W_600,
                                    color=INK,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        item.get("status", "expected").capitalize(),
                                        size=11,
                                        color=MUTED,
                                    ),
                                    border=ft.Border.all(1, BORDER),
                                    border_radius=20,
                                    padding=ft.Padding.symmetric(
                                        horizontal=10, vertical=3
                                    ),
                                ),
                            ],
                        ),
                        labeled("Amount", amount),
                        labeled("Expected date", when.field),
                        text_button("Remove", remove),
                    ],
                )
            )
        ]
        self.rows.controls.append(row)
        self.page.update()

    def body(self):
        return [
            self.rows,
            self.add_button,
            note("Leave an item out if you are not sure yet.", bg=NOTE_BG),
            ft.Divider(color=BORDER),
        ]

    def payload(self) -> dict:
        items = []
        for row in self.rows.controls:
            refs = row.data
            source = refs["source"].value.strip()
            amount = _to_amount(refs["amount"].value)
            if not source and not amount:
                continue
            if not source:
                raise ValueError("Give each income a source.")
            if not amount:
                raise ValueError(f"Enter an amount for {source}.")
            items.append(
                {
                    "source": source,
                    "amount": amount,
                    "expected_date": refs["date"].value or date.today().isoformat(),
                }
            )
        return {"expected_incomes": items}


# ---------------------------------------------------------------------------
# Step 4 — What must you pay?
# ---------------------------------------------------------------------------
class CommitmentsStep(OnboardingScreen):
    step = 4
    title = "What must you pay?"
    subtitle = "Add essential expenses and upcoming commitments."

    def __init__(self, page, app):
        super().__init__(page, app)
        existing = app.commitments or []
        self.rows = ft.Column(spacing=12, controls=[])
        for item in existing or [{}]:
            self._add_row(item)
        self.add_button = ft.Button(
            content="+ Add another expense",
            color=INK,
            style=ft.ButtonStyle(
                bgcolor=SURFACE,
                side=ft.BorderSide(1, BORDER),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=lambda e: self._add_row({}),
        )

    def _add_row(self, item: dict):
        name = style_input(ft.TextField(label="e.g. Apartment rent", value=item.get("name") or ""))
        amount = style_input(
            ft.TextField(
                label="R 0",
                value=_shown_amount(item.get("amount")),
                keyboard_type=ft.KeyboardType.NUMBER,
            )
        )
        due = DateField(self.page, "dd/mm/yyyy")
        if item.get("due_date"):
            due.value = item["due_date"]

        row = ft.Column(spacing=10)
        row.data = {"name": name, "amount": amount, "date": due}

        def remove(e, r=row):
            self.rows.controls.remove(r)
            self.page.update()

        row.controls = [
            card(
                ft.Column(
                    spacing=10,
                    controls=[
                        labeled("Expense", name),
                        labeled("Amount", amount),
                        labeled("Due date", due.field),
                        text_button("Remove", remove),
                    ],
                )
            )
        ]
        self.rows.controls.append(row)
        self.page.update()

    def body(self):
        return [
            self.rows,
            self.add_button,
            note(
                "Only add bills you have to pay. Leave an item out if you "
                "are not sure yet."
            ),
            ft.Divider(color=BORDER),
        ]

    def payload(self) -> dict:
        items = []
        for row in self.rows.controls:
            refs = row.data
            name = refs["name"].value.strip()
            amount = _to_amount(refs["amount"].value)
            # PUT replaces the whole list, so untouched blank rows are dropped.
            if not name and not amount:
                continue
            if not name:
                raise ValueError("Give each expense a name.")
            if not amount:
                raise ValueError(f"Enter an amount for {name}.")
            items.append(
                {
                    "name": name,
                    "amount": amount,
                    "due_date": refs["date"].value,
                }
            )
        return items

    def footer(self):
        return nav_footer(
            on_back=lambda e: self.save_and(exit_on_success=True),
            on_continue=lambda e: self.save_and(next_step=5),
            continue_label="Review & continue",
        )

    async def _save(self, next_step, exit_on_success):
        set_error(self.error, None, self.page)
        try:
            await self.app.api.save_commitments(self.payload())
            await self.app.api.set_step(4)
        except ValueError as exc:
            set_error(self.error, str(exc), self.page)
            return
        except Exception as exc:  # noqa: BLE001
            set_error(self.error, error_message(exc), self.page)
            return
        if exit_on_success:
            await self.app.open_dashboard()
            return
        await self.app.reload_draft()
        self.app.show_step(5)


# ---------------------------------------------------------------------------
# Step 5 — Set your first savings goal
# ---------------------------------------------------------------------------
def goal_form_view(page: ft.Page, app) -> ft.View:
    """Step 5 of the wireframe: create a first savings goal, or skip.

    "Skip for now" and "Save & exit" still complete onboarding — the backend
    needs only the financial profile and balance for that.
    """

    draft = app.draft or {}
    goals = draft.get("savings_goals") or []
    goal = goals[0] if goals else {}
    error = error_text()

    name = style_input(ft.TextField(label="e.g. Emergency buffer", value=goal.get("name") or ""))
    target = style_input(
        ft.TextField(
            label="R 0",
            value=_shown_amount(goal.get("target_amount")),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
    )
    saved = style_input(
        ft.TextField(
            label="R 0",
            value=_shown_amount(goal.get("saved_amount")),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
    )
    target_date = DateField(page, "dd/mm/yyyy")
    if goal.get("target_date"):
        target_date.value = goal["target_date"]
    priority = style_input(
        ft.Dropdown(value=goal.get("priority") or "medium", options=PRIORITIES)
    )

    saving = ft.Text(size=13, color=MUTED, visible=False)

    async def run_goal(action):
        """Run a button action; ignore taps while one is in flight."""

        if saving.visible:
            return
        if app.resuming:
            # Reopened at the goal step, so onboarding is effectively over:
            # go to the review rather than silently creating an empty goal.
            await app.show_starting_picture()
            return
        saving.value = "Saving…"
        saving.visible = True
        page.update()
        try:
            await action()
        finally:
            saving.visible = False
            page.update()

    async def save_goal(e=None):
        set_error(error, None, page)
        try:
            target_amount = _to_amount(target.value)
            if not name.value.strip():
                raise ValueError("Goal name is required.")
            if not target_amount:
                raise ValueError("Target amount is required.")
            item = {
                "name": name.value.strip(),
                "target_amount": target_amount,
                "saved_amount": _to_amount(saved.value) or "0",
                "target_date": target_date.value,
                "priority": priority.value,
            }
            # savings_goals is replace-on-write: send this goal first, then
            # any further goals that already exist.
            await app.api.patch_onboarding(savings_goals=[item, *goals[1:]])
            await app.api.set_step(5)
            await app.api.complete_onboarding()
        except ValueError as exc:
            set_error(error, str(exc), page)
            return
        except Exception as exc:  # noqa: BLE001
            set_error(error, error_message(exc), page)
            return
        # Goals are optional, so onboarding is done: show the review.
        await app.show_starting_picture()

    async def skip(e=None):
        try:
            await app.api.set_step(5)
            await app.api.complete_onboarding()
        except Exception as exc:  # noqa: BLE001
            set_error(error, error_message(exc), page)
            return
        await app.show_starting_picture()

    body = [
        labeled("Goal name *", name),
        labeled("Target amount *", target),
        labeled("Already saved", saved),
        labeled("Target date (optional)", target_date.field),
        labeled("Priority (optional)", priority),
        error,
        saving,
        ft.Divider(color=BORDER),
        ft.Row(
            spacing=10,
            controls=[
                ft.Column(
                    expand=True,
                    controls=[
                        secondary_button(
                            "Skip for now",
                            lambda e: page.run_task(run_goal, skip),
                            expand=True,
                        )
                    ],
                ),
                ft.Column(
                    expand=True,
                    controls=[
                        primary_button(
                            "Create goal",
                            lambda e: page.run_task(run_goal, save_goal),
                            expand=True,
                        )
                    ],
                ),
            ],
        ),
    ]

    return onboarding_view(
        page,
        step=5,
        title="Set your first savings goal",
        subtitle="Optional. You can create or change goals at any time.",
        body=body,
        footer=None,
        on_save_exit=lambda e: page.run_task(run_goal, skip),
        scroll=True,
    )


# ---------------------------------------------------------------------------
# Your starting picture — the review before the dashboard
# ---------------------------------------------------------------------------
def _figure(label: str, value: str, strong: bool = False) -> ft.Column:
    return ft.Column(
        spacing=2,
        controls=[
            ft.Text(label, size=12, color=MUTED),
            ft.Text(
                value,
                size=20 if strong else 16,
                weight=ft.FontWeight.W_700 if strong else ft.FontWeight.W_500,
                color=INK,
            ),
        ],
    )


def starting_picture_view(page: ft.Page, app, overview: dict) -> ft.View:
    """Reads GET /api/dashboard/overview so the numbers match the dashboard."""

    currency = overview.get("currency") or "ZAR"
    next_payment = overview.get("next_expected_payment") or {}
    goals = overview.get("savings_goals") or []

    next_label = "No expected payment yet"
    if next_payment:
        next_label = (
            f"Next income  +{money(next_payment.get('amount'), currency)}  "
            f"{format_date(next_payment.get('expected_date'))}"
        )

    controls: list[ft.Control] = [
        progress_header(5),
        step_title(
            "Your starting picture",
            "This is an estimate built from what you told us.",
        ),
        card(
            ft.Column(
                spacing=18,
                controls=[
                    _figure("Available now", money(overview.get("available_now"), currency), True),
                    ft.Divider(color=BORDER),
                    _figure(
                        "Projected after known events",
                        money(overview.get("projected_balance"), currency),
                        True,
                    ),
                    ft.Text(next_label, size=13, color=MUTED),
                    ft.Divider(color=BORDER),
                    ft.Row(
                        spacing=16,
                        controls=[
                            ft.Column(
                                expand=True,
                                controls=[
                                    _figure("Before your next", "expected payment"),
                                ],
                            ),
                            _figure(
                                "Essential commitments",
                                money(overview.get("essential_commitments"), currency),
                            ),
                        ],
                    ),
                ],
            )
        ),
    ]

    if goals:
        controls.append(
            card(
                ft.Column(
                    spacing=8,
                    controls=[
                        ft.Text("Savings goal", size=12, weight=ft.FontWeight.W_600, color=INK),
                        ft.Text(goals[0].get("name") or "Goal", size=15, color=INK),
                        ft.Text(
                            f"{money(goals[0].get('saved_amount'), currency)} of "
                            f"{money(goals[0].get('target_amount'), currency)}",
                            size=13,
                            color=MUTED,
                        ),
                    ],
                )
            )
        )

    controls.append(
        note(
            "Your forecast is an estimate. It updates as you add payments and "
            "expenses, so nothing here is locked in."
        )
    )

    return ft.View(
        route="/",
        bgcolor=BG,
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=8),
                content=top_bar(
                    on_save_exit=lambda e: page.run_task(app.open_dashboard)
                ),
            ),
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=8),
                content=ft.Column(
                    spacing=18,
                    controls=[
                        *controls,
                        primary_button(
                            "Go to my dashboard",
                            lambda e: page.run_task(app.open_dashboard),
                            expand=True,
                        ),
                    ],
                ),
            ),
            ft.Container(height=8),
        ],
    )
