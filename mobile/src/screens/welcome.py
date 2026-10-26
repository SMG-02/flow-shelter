"""Welcome screen — the first screen a user sees (design: screens/s1.png).

Holds the product promise, the language picker, and the two entry points into
authentication. Tapping "Create account" or "Log in" swaps the auth form in
below the copy instead of navigating away.
"""

import flet as ft

from screens.auth import AuthPanel
from theme import (
    BG,
    BORDER,
    INK,
    MUTED,
    RADIUS,
    logo,
    primary_button,
    secondary_button,
    style_input,
)

LANGUAGES = {
    "en": "English",
    "zu": "isiZulu",
    "af": "Afrikaans",
    "xh": "isiXhosa",
    "st": "Sesotho",
}

LANGUAGE_PREF_KEY = "language"


class WelcomeScreen:
    def __init__(self, page: ft.Page, app):
        self.page = page
        self.app = app
        self.prefs = ft.SharedPreferences()

        self.language = style_input(
            ft.Dropdown(
                value="en",
                options=[
                    ft.DropdownOption(key=code, text=name)
                    for code, name in LANGUAGES.items()
                ],
                # Flet 1.x fires on_select (on_change does not exist here).
                on_select=self._language_changed,
            )
        )

        self.actions = ft.Row(
            spacing=10,
            controls=[
                ft.Column(
                    expand=True,
                    controls=[
                        primary_button(
                            "Create account",
                            lambda e: self.show_auth(register=True),
                            expand=True,
                        )
                    ],
                ),
                ft.Column(
                    expand=True,
                    controls=[
                        secondary_button(
                            "Log in",
                            lambda e: self.show_auth(register=False),
                            expand=True,
                        )
                    ],
                ),
            ],
        )

        self.form_slot = ft.Column(tight=True, spacing=12, controls=[])

        self.body = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                logo(),
                ft.Container(expand=True),
                ft.Text(
                    "MONEY PLANNING FOR FREELANCERS",
                    size=11,
                    weight=ft.FontWeight.W_600,
                    color=MUTED,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Know what is safe to spend.",
                    size=34,
                    weight=ft.FontWeight.W_700,
                    color=INK,
                ),
                ft.Container(height=8),
                ft.Text(
                    "Plan around irregular income, essential bills and savings "
                    "goals — without the guesswork.",
                    size=15,
                    color=MUTED,
                ),
                ft.Container(height=28),
                ft.Text("Language", size=13, weight=ft.FontWeight.W_600, color=INK),
                ft.Container(height=6),
                self.language,
                ft.Container(height=16),
                self.actions,
                self.form_slot,
                ft.Container(height=12),
                ft.Text(
                    "Your language preference is saved on this device.",
                    size=11,
                    color=MUTED,
                ),
                ft.Container(height=24),
            ],
        )

        self.page.run_task(self._restore_language)

    # ---- layout ----------------------------------------------------------
    def view(self) -> ft.View:
        return ft.View(
            route="/",
            padding=ft.Padding.symmetric(horizontal=24, vertical=16),
            bgcolor=BG,
            controls=[self.body],
            scroll=ft.ScrollMode.AUTO,
        )

    def show_auth(self, register: bool):
        self.actions.visible = False
        self.form_slot.controls = [AuthPanel(self.app, register)]
        self.page.update()

    def show_welcome(self):
        self.form_slot.controls = []
        self.actions.visible = True
        self.page.update()

    # ---- language --------------------------------------------------------
    async def _restore_language(self):
        saved = await self.prefs.get(LANGUAGE_PREF_KEY)
        if saved in LANGUAGES:
            self.language.value = saved
            self.page.update()

    def _language_changed(self, e):
        self.page.run_task(
            self.prefs.set, LANGUAGE_PREF_KEY, self.language.value or "en"
        )
