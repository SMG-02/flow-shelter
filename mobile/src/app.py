"""App controller: owns state, decides which screen is showing.

Flow
  start → saved token? ─no→ welcome ─auth→ onboarding or dashboard
                        └yes→ (onboarding complete?) → dashboard
                              (otherwise) → onboarding at the saved step
"""

import flet as ft

from api.client import Api, Unauthenticated, error_message
from screens.dashboard import DashboardScreen
from screens.onboarding import (
    BalanceStep,
    CommitmentsStep,
    IncomeStep,
    WorkStep,
    goal_form_view,
    starting_picture_view,
)
from screens.welcome import WelcomeScreen
from theme import BG, INK, MUTED, SURFACE

STEPS = {
    1: WorkStep,
    2: BalanceStep,
    3: IncomeStep,
    4: CommitmentsStep,
}

MAX_STEP = 5


class FlowShelterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.api = Api()

        # Server state, refreshed rather than mutated from the UI.
        self.draft: dict = {}
        self.commitments: list[dict] = []
        self.overview: dict = {}

        # True while re-entering a saved draft: the goal form then opens the
        # review instead of creating a goal.
        self.resuming = False

        self.welcome = WelcomeScreen(page, self)
        self.dashboard = DashboardScreen(page, self)

        self._configure_page()

    def _configure_page(self):
        self.page.title = "Flow Shelter"
        self.page.bgcolor = BG
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 400
        self.page.window.height = 860
        self.page.window.min_width = 320

    # ---- startup ---------------------------------------------------------
    async def start(self):
        prefs = ft.SharedPreferences()
        await self.api.load_token(prefs)
        if not self.api.is_authenticated:
            self.show_welcome()
            return

        try:
            await self.reload_draft()
        except Unauthenticated:
            await self.api.clear_token()
            self.show_welcome()
            return
        except Exception as exc:  # noqa: BLE001 - offline start
            self.show_offline(error_message(exc))
            return

        if self.draft.get("is_complete"):
            await self.open_dashboard()
        else:
            # current_step is 1..5. A screen saves its own step when moving
            # on, so reopening resumes at the same screen, not the next one.
            self.show_step(self.draft.get("current_step") or 1, resume=True)

    # ---- navigation ------------------------------------------------------
    def show_welcome(self):
        self._reset_views()
        self.welcome.show_welcome()
        self.page.views.append(self.welcome.view())
        self.page.update()

    def show_auth(self, register: bool):
        self.welcome.show_auth(register)

    def show_step(self, step: int, resume: bool = False):
        step = max(1, min(step, MAX_STEP))
        self.resuming = resume
        if step == 5:
            self.page.run_task(self.show_goal_form)
            return
        screen = STEPS[step](self.page, self)
        self._replace_view(screen.view())

    async def show_goal_form(self):
        self._replace_view(goal_form_view(self.page, self))

    async def show_starting_picture(self):
        try:
            self.overview = await self.api.overview()
        except Unauthenticated:
            await self.logout()
            return
        except Exception as exc:  # noqa: BLE001
            self.show_offline(error_message(exc))
            return
        self._replace_view(starting_picture_view(self.page, self, self.overview))

    async def open_dashboard(self):
        try:
            await self.dashboard.load()
        except Unauthenticated:
            await self.logout()
            return
        self._replace_view(self.dashboard.view())

    async def on_authenticated(self):
        await self.start()

    async def logout(self):
        await self.api.clear_token()
        self.draft = {}
        self.commitments = []
        self.overview = {}
        self.show_welcome()

    # ---- data ------------------------------------------------------------
    async def reload_draft(self):
        self.draft = await self.api.get_onboarding()
        data = await self.api.get_commitments()
        self.commitments = data.get("commitments") or []

    async def start_onboarding(self):
        """Re-enter onboarding from the dashboard at the first step."""
        try:
            await self.reload_draft()
        except Unauthenticated:
            await self.logout()
            return
        except Exception as exc:  # noqa: BLE001
            self.show_offline(error_message(exc))
            return
        self.show_step(1)

    # ---- view helpers ----------------------------------------------------
    def _reset_views(self):
        self.page.views.clear()

    def _replace_view(self, view: ft.View):
        # Wrap so a repeated call always lands on the last view (Flet refuses
        # duplicate routes in page.views).
        view.route = f"/screen/{id(view)}"
        self.page.views.append(view)
        self.page.update()

    def show_offline(self, message: str):
        self._reset_views()
        self.page.views.append(
            ft.View(
                route="/offline",
                bgcolor=BG,
                padding=24,
                controls=[
                    ft.Container(expand=True),
                    ft.Text("Can't load your plan", size=22, weight=ft.FontWeight.W_700, color=INK),
                    ft.Text(message, size=14, color=MUTED),
                    ft.Container(height=16),
                    ft.FilledButton(
                        content="Try again",
                        bgcolor=INK,
                        color=SURFACE,
                        height=46,
                        on_click=lambda e: self.page.run_task(self.start),
                    ),
                    ft.Container(expand=True),
                ],
            )
        )
        self.page.update()


def main(page: ft.Page):
    # main.py is the entry point; keep startup here so `flet run src/app.py`
    # behaves the same way.
    app = FlowShelterApp(page)
    page.run_task(app.start)


if __name__ == "__main__":
    ft.run(main)
