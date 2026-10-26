"""Sign up / log in on top of the welcome screen.

Wireframe s1.png shows the welcome content with two buttons. Tapping either
swaps in the matching form here, which talks to /auth/register and
/auth/login. On success `app.on_authenticated()` decides the next screen.
"""

import flet as ft

from api.client import error_message
from theme import INK, primary_button, secondary_button, style_input, text_button
from widgets import error_text, set_error

MIN_PASSWORD = 12


class AuthPanel(ft.Column):
    """The form swapped into the welcome screen."""

    def __init__(self, app, register: bool):
        self.app = app
        self.register = register
        self.busy = False

        self.name = style_input(
            ft.TextField(
                label="Name",
                capitalization=ft.TextCapitalization.WORDS,
                autofocus=True,
            )
        )
        self.email = style_input(
            ft.TextField(label="Email", keyboard_type=ft.KeyboardType.EMAIL)
        )
        self.password = style_input(
            ft.TextField(
                label="Password",
                hint_text=f"At least {MIN_PASSWORD} characters",
                password=True,
                can_reveal_password=True,
                on_submit=lambda e: self._submit(),
            )
        )
        self.error = error_text()
        self.submit = primary_button(
            "Create account" if register else "Log in",
            lambda e: self._submit(),
            expand=True,
        )

        super().__init__(
            tight=True,
            spacing=12,
            controls=[
                ft.Text(
                    "Create your account" if register else "Welcome back",
                    size=18,
                    weight=ft.FontWeight.W_600,
                    color=INK,
                ),
                *([self.name] if register else []),
                self.email,
                self.password,
                self.error,
                ft.Row(
                    spacing=10,
                    controls=[
                        secondary_button(
                            "Back", lambda e: self.app.show_welcome(), expand=True
                        ),
                        self.submit,
                    ],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        text_button(
                            "Already have an account? Log in"
                            if register
                            else "New here? Create an account",
                            lambda e: self.app.show_auth(not register),
                        )
                    ],
                ),
            ],
        )

    def _validate(self) -> str | None:
        if self.register and len(self.name.value.strip()) < 2:
            return "Enter your name."
        if "@" not in self.email.value or "." not in self.email.value.split("@")[-1]:
            return "Enter a valid email address."
        if self.register and len(self.password.value) < MIN_PASSWORD:
            return f"Password must be at least {MIN_PASSWORD} characters."
        if not self.password.value:
            return "Enter your password."
        return None

    def _submit(self):
        if self.busy:
            return
        problem = self._validate()
        if problem:
            set_error(self.error, problem, self.app.page)
            return

        set_error(self.error, None, self.app.page)
        self.busy = True
        self.submit.disabled = True
        self.app.page.update()
        self.app.page.run_task(self._call_api)

    async def _call_api(self):
        try:
            if self.register:
                await self.app.api.register(
                    self.name.value.strip(),
                    self.email.value.strip().lower(),
                    self.password.value,
                )
            await self.app.api.login(
                self.email.value.strip().lower(), self.password.value
            )
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            set_error(self.error, error_message(exc), self.app.page)
            self.busy = False
            self.submit.disabled = False
            self.app.page.update()
            return

        self.busy = False
        self.submit.disabled = False
        await self.app.on_authenticated()
