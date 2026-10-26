"""Home dashboard (design: Screenshot 2026-10-25 080930.png).

Built from GET /api/dashboard/overview, which already includes the alerts,
so the alert banner, the money cards and the greeting all come from one
response, re-fetched every time the screen opens.

The bottom bar mirrors the wireframe. Only Overview has a screen behind it;
the other tabs point back here rather than faking a destination that does
not exist in the API yet.
"""

from datetime import datetime

import flet as ft

from api.client import Unauthenticated, error_message
from theme import (
    BG,
    BORDER,
    INK,
    MUTED,
    SURFACE,
    WARN_BG,
    caption,
    format_date,
    money,
    primary_button,
    text_button,
)
from widgets import card

TABS = [
    ("overview", "Overview", ft.Icons.HOME_OUTLINED),
    ("cashflow", "Cash flow", ft.Icons.INSIGHTS_OUTLINED),
    ("transactions", "Transactions", ft.Icons.SWAP_VERT_OUTLINED),
    ("goals", "Goals", ft.Icons.FLAG_OUTLINED),
]


def greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def money_card(label: str, amount: str, detail: str) -> ft.Container:
    return card(
        ft.Column(
            spacing=6,
            controls=[
                caption(label.upper()),
                ft.Text(amount, size=30, weight=ft.FontWeight.W_700, color=INK),
                ft.Text(detail, size=13, color=MUTED),
            ],
        )
    )


def alert_banner(alert: dict, on_review) -> ft.Container:
    severity_colour = "#C9A227" if alert.get("severity") == "warning" else BORDER
    return ft.Container(
        bgcolor=WARN_BG,
        padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        border=ft.Border(left=ft.BorderSide(3, severity_colour)),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Text(
                    alert.get("message") or "Something needs your attention.",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=INK,
                ),
                text_button("Review", on_review),
            ],
        ),
    )


class DashboardScreen:
    def __init__(self, page: ft.Page, app):
        self.page = page
        self.app = app
        self.default_currency = "ZAR"

        self.content = ft.Column(spacing=12, controls=[])
        self.body = ft.Column(
            expand=True,
            spacing=12,
            controls=[self.content],
            scroll=ft.ScrollMode.AUTO,
        )
        self.loading = ft.ProgressBar(
            visible=True, color=INK, bgcolor=BORDER, bar_height=2
        )

        # Flet 1.x has no pull-to-refresh control; the dashboard re-fetches
        # every time it is opened through app.open_dashboard().
        self.scrollable = ft.Column(
            expand=True,
            spacing=0,
            controls=[self.loading, self.body],
        )

        self.view_control = ft.View(
            route="/dashboard",
            bgcolor=BG,
            padding=0,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                    content=self._top_bar(),
                ),
                self.scrollable,
                self._bottom_nav(),
            ],
        )

    # ---- layout ----------------------------------------------------------
    def _top_bar(self) -> ft.Row:
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    spacing=0,
                    controls=[
                        ft.Text("FLOWSHELTER", size=9, color=MUTED),
                        ft.Text(
                            "Overview",
                            size=18,
                            weight=ft.FontWeight.W_600,
                            color=INK,
                        ),
                    ],
                ),
                ft.Row(
                    spacing=12,
                    controls=[
                        ft.Icon(ft.Icons.WB_SUNNY_OUTLINED, size=18, color=INK),
                        ft.Container(
                            width=30,
                            height=30,
                            bgcolor=BORDER,
                            border_radius=15,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(self._initials(), size=11, color=INK),
                        ),
                    ],
                ),
            ],
        )

    def _initials(self) -> str:
        user = (self.app.overview or {}).get("user") or {}
        name = (user.get("name") or "").strip()
        parts = [p for p in name.split() if p]
        if not parts:
            return "?"
        return "".join(p[0].upper() for p in parts[:2])

    def _bottom_nav(self) -> ft.Container:
        items = []
        for key, label, icon in TABS:
            active = key == "overview"
            items.append(
                ft.Container(
                    expand=True,
                    on_click=(None if active
                              else (lambda e, l=label: self._not_available(l))),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                        controls=[
                            ft.Icon(
                                icon,
                                size=18,
                                color=INK if active else MUTED,
                            ),
                            ft.Text(
                                label,
                                size=10,
                                weight=ft.FontWeight.W_600 if active else None,
                                color=INK if active else MUTED,
                            ),
                        ],
                    ),
                )
            )
        return ft.Container(
            bgcolor=SURFACE,
            border=ft.Border(top=ft.BorderSide(1, BORDER)),
            padding=ft.Padding.symmetric(vertical=8),
            content=ft.Row(spacing=0, controls=items),
        )

    # ---- data ------------------------------------------------------------
    def view(self) -> ft.View:
        return self.view_control

    async def load(self):
        self.loading.visible = True
        self.page.update()
        try:
            self.app.overview = await self.app.api.overview()
        except Unauthenticated:
            await self.app.logout()
            return
        except Exception as exc:  # noqa: BLE001
            self.content.controls = [
                card(ft.Text(error_message(exc), size=14, color=INK))
            ]
            self.loading.visible = False
            self.page.update()
            return
        self.render()
        self.loading.visible = False
        self.page.update()

    def render(self):
        # The avatar initials depend on the response, so rebuild the bar too.
        self.view_control.controls[0].content = self._top_bar()

        overview = self.app.overview or {}
        currency = overview.get("currency") or self.default_currency
        user = overview.get("user") or {}
        name = (user.get("name") or "").split(" ")[0] or "there"
        next_payment = overview.get("next_expected_payment") or {}
        alerts = overview.get("alerts") or []

        if next_payment.get("expected_date"):
            lead = (
                "Here is what needs your attention before "
                f"{format_date(next_payment['expected_date'])}."
            )
        else:
            lead = "Add an expected payment to see what is coming up."

        controls: list[ft.Control] = [
            caption("ILLUSTRATIVE DATA"),
            ft.Text(
                f"{greeting()}, {name}",
                size=26,
                weight=ft.FontWeight.W_700,
                color=INK,
            ),
            ft.Text(lead, size=14, color=MUTED),
            primary_button(
                "+ Add transaction",
                lambda e: self._not_available("Adding transactions"),
                expand=True,
            ),
        ]

        for alert in alerts[:2]:
            controls.append(alert_banner(alert, lambda e: self._not_available("Review")))

        controls.append(
            money_card(
                "Available now",
                money(overview.get("available_now"), currency),
                "Confirmed money you can use today",
            )
        )
        controls.append(
            money_card(
                "Projected after planned events",
                money(overview.get("projected_balance"), currency),
                "Estimate if expected income arrives"
                if overview.get("forecast_is_estimate", True)
                else "Projected from your latest update",
            )
        )

        if next_payment:
            controls.append(
                ft.Container(
                    bgcolor=INK,
                    border_radius=8,
                    padding=16,
                    content=ft.Column(
                        spacing=6,
                        controls=[
                            ft.Text(
                                "NEXT EXPECTED PAYMENT",
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=BORDER,
                            ),
                            ft.Text(
                                money(next_payment.get("amount"), currency),
                                size=30,
                                weight=ft.FontWeight.W_700,
                                color=SURFACE,
                            ),
                            ft.Text(
                                f"{next_payment.get('source') or 'Expected'} · "
                                f"{format_date(next_payment.get('expected_date'))}",
                                size=13,
                                color=BORDER,
                            ),
                        ],
                    ),
                )
            )

        goals = overview.get("savings_goals") or []
        if goals:
            goal = goals[0]
            controls.append(
                card(
                    ft.Column(
                        spacing=8,
                        controls=[
                            caption("SAVINGS GOAL"),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(goal.get("name") or "Goal", size=16, color=INK),
                                    ft.Text(
                                        f"{round(goal.get('progress_percentage') or 0)}%",
                                        size=14,
                                        weight=ft.FontWeight.W_600,
                                        color=INK,
                                    ),
                                ],
                            ),
                            ft.ProgressBar(
                                value=min(
                                    float(goal.get("progress_percentage") or 0) / 100, 1
                                ),
                                color=INK,
                                bgcolor=BORDER,
                                bar_height=6,
                                border_radius=3,
                            ),
                            ft.Text(
                                f"{money(goal.get('saved_amount'), currency)} saved of "
                                f"{money(goal.get('target_amount'), currency)}",
                                size=13,
                                color=MUTED,
                            ),
                        ],
                    )
                )
            )

        controls.append(
            ft.Container(
                padding=ft.Padding.only(top=8),
                content=text_button(
                    "Edit my plan",
                    lambda e: self.page.run_task(self.app.start_onboarding),
                ),
            )
        )

        self.content.controls = controls
        self.page.update()

    def _not_available(self, what: str):
        self.page.show_dialog(
            ft.SnackBar(ft.Text(f"{what} is not available yet."))
        )
