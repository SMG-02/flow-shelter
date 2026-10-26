"""Reusable pieces of the onboarding chrome and form controls."""

from datetime import date, datetime

import flet as ft

from theme import (
    BG,
    BORDER,
    ERROR,
    INK,
    MUTED,
    PAD,
    RADIUS,
    SURFACE,
    logo,
    style_input,
)


class DateField:
    """A read-only text field that opens a DatePicker dialog.

    Exposes `.value` as an ISO date string (`YYYY-MM-DD`) or None.
    """

    def __init__(self, page: ft.Page, label: str):
        self.page = page
        self._selected: date | None = None
        self.field = style_input(
            ft.TextField(
                label=label,
                hint_text="dd/mm/yyyy",
                read_only=True,
                on_click=self._open,
                suffix_icon=ft.Icon(ft.Icons.CALENDAR_TODAY, size=18, color=MUTED),
            )
        )
        self.picker = ft.DatePicker(
            first_date=date.today().replace(year=date.today().year - 1),
            last_date=date.today().replace(year=date.today().year + 5),
            on_change=self._picked,
        )

    @property
    def value(self) -> str | None:
        return self._selected.isoformat() if self._selected else None

    @value.setter
    def value(self, iso):
        if not iso:
            self._selected = None
            self.field.value = ""
            return
        try:
            self._selected = date.fromisoformat(str(iso)[:10])
            self.field.value = self._selected.strftime("%d/%m/%Y")
        except ValueError:
            self._selected = None
            self.field.value = ""

    def _open(self, e=None):
        self.page.show_dialog(self.picker)

    def _picked(self, e):
        raw = self.picker.value
        if isinstance(raw, str):
            try:
                raw = datetime.fromisoformat(raw)
            except ValueError:
                return
        if raw is not None:
            self._selected = raw.date() if hasattr(raw, "date") else raw
            self.field.value = self._selected.strftime("%d/%m/%Y")
        else:
            self._selected = None
            self.field.value = ""
        self.page.pop_dialog()
        self.page.update()


def top_bar(on_save_exit=None, right_text: str | None = None) -> ft.Row:
    """Logo on the left; either a title or 'Save & exit' on the right."""

    if on_save_exit is not None:
        right: ft.Control = ft.TextButton(
            content=ft.Text("Save & exit", size=13, color=INK),
            style=ft.ButtonStyle(
                overlay_color=ft.Colors.TRANSPARENT,
                padding=ft.Padding.symmetric(horizontal=0),
            ),
            on_click=on_save_exit,
        )
    else:
        right = ft.Text(
            right_text or "", size=13, weight=ft.FontWeight.W_600, color=INK
        )
    return ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[logo(), right],
    )


def progress_header(step: int, total: int = 5) -> ft.Control:
    """'Set up your plan · Step N of M' + progress bar."""

    return ft.Column(
        spacing=10,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("Set up your plan", size=13, color=INK),
                    ft.Text(
                        f"Step {step} of {total}",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=INK,
                    ),
                ],
            ),
            ft.ProgressBar(
                value=step / total,
                color=INK,
                bgcolor=BORDER,
                bar_height=4,
                border_radius=2,
            ),
        ],
    )


def step_title(title: str, subtitle: str | None = None) -> ft.Column:
    controls: list[ft.Control] = [
        ft.Text(title, size=26, weight=ft.FontWeight.W_700, color=INK)
    ]
    if subtitle:
        controls.append(ft.Text(subtitle, size=14, color=MUTED))
    return ft.Column(spacing=8, controls=controls)


def field_label(text: str) -> ft.Text:
    return ft.Text(text, size=12, weight=ft.FontWeight.W_600, color=INK)


def labeled(text: str, control: ft.Control) -> ft.Column:
    return ft.Column(spacing=6, controls=[field_label(text), control])


def error_text() -> ft.Text:
    return ft.Text(size=13, color=ERROR, visible=False)


def set_error(control: ft.Text, message: str | None, page: ft.Page) -> None:
    control.value = message or ""
    control.visible = bool(message)
    page.update()


def card(content: ft.Control, padding: int = 16) -> ft.Container:
    return ft.Container(
        bgcolor=SURFACE,
        border=ft.Border.all(1, BORDER),
        border_radius=RADIUS,
        padding=padding,
        content=content,
    )


def onboarding_view(
    page: ft.Page,
    step: int,
    title: str,
    subtitle: str | None,
    body: list[ft.Control],
    footer: ft.Control,
    on_save_exit=None,
    scroll: bool = False,
) -> ft.View:
    """Common onboarding layout: top bar, header card with title, body, footer."""

    steps = ft.Column(
        spacing=18,
        controls=[
            progress_header(step),
            step_title(title, subtitle),
            *body,
        ],
    )

    page_content = ft.Column(
        spacing=4,
        controls=[steps] + ([footer] if footer is not None else []),
    )

    return ft.View(
        route="/",
        bgcolor=BG,
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        controls=[
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=8),
                content=top_bar(on_save_exit=on_save_exit),
            ),
            card(page_content, padding=PAD),
            ft.Container(height=8),
        ],
        scroll=ft.ScrollMode.AUTO if scroll else ft.ScrollMode.ADAPTIVE,
    )


def nav_footer(on_back=None, on_continue=None, continue_label="Continue",
               back_label="Back", skip_label: str | None = None) -> ft.Row:
    """Bottom row: optional secondary button on the left, primary on the right."""

    left: list[ft.Control] = []
    if skip_label is not None:
        left.append(
            ft.TextButton(
                content=ft.Text(skip_label, size=13, color=INK),
                style=ft.ButtonStyle(
                    overlay_color=ft.Colors.TRANSPARENT,
                    padding=ft.Padding.symmetric(horizontal=0),
                ),
                on_click=on_back,
            )
        )
    elif on_back is not None:
        left.append(
            ft.Column(
                expand=True,
                controls=[
                    ft.Button(
                        content=back_label,
                        color=INK,
                        height=46,
                        style=ft.ButtonStyle(
                            bgcolor=SURFACE,
                            side=ft.BorderSide(1, BORDER),
                            shape=ft.RoundedRectangleBorder(radius=RADIUS),
                        ),
                        on_click=on_back,
                    )
                ],
            )
        )

    return ft.Row(
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=left
        + [
            ft.FilledButton(
                content=continue_label,
                bgcolor=INK,
                color=BG,
                height=46,
                expand=True,
                on_click=on_continue,
            )
        ],
    )
