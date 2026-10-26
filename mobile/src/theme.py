"""Shared colours, spacing and formatting for every screen.

Mirrors the Figma wireframes: warm off-white canvas, near-black ink for
primary actions, muted grey-green for secondary text, and thin grey borders.
"""

import flet as ft

BG = "#F5F7F2"
SURFACE = "#FFFFFF"
INK = "#1B2A23"
MUTED = "#64736A"
BORDER = "#D5DCD5"
NOTE_BG = "#ECEFEA"
WARN_BG = "#F3EFE2"
ERROR = "#B3261E"

RADIUS = 8
PAD = 20


def money(amount, currency: str = "ZAR") -> str:
    """Format an API money string ("18450.0") as "R 18 450".

    Groups thousands with a thin-looking space, as in the wireframes.
    """

    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0.0

    cents = round(value, 2)
    whole = int(abs(cents))
    fractional = round((abs(cents) - whole) * 100)

    grouped = f"{whole:,}".replace(",", " ")
    text = f"{grouped}.{fractional:02d}" if fractional else grouped
    sign = "-" if cents < 0 else ""
    return f"{sign}R {text}" if currency == "ZAR" else f"{sign}{text} {currency}"


def format_date(iso_date) -> str:
    """'2026-06-28' -> '28 Jun 2026'."""

    if not iso_date:
        return "Not set"
    from datetime import date

    try:
        d = date.fromisoformat(str(iso_date)[:10])
    except ValueError:
        return str(iso_date)
    return f"{d.day:02d} {d:%b %Y}"


def style_input(control: ft.Control) -> ft.Control:
    """Apply the shared outlined-input look to a TextField / Dropdown."""

    control.text_size = 15
    control.border = ft.OutlineInputBorder(
        border_radius=ft.BorderRadius.all(RADIUS),
        side=ft.BorderSide(1, BORDER),
    )
    control.content_padding = ft.Padding.symmetric(horizontal=12, vertical=14)
    return control


def caption(text: str) -> ft.Text:
    return ft.Text(text, size=11, weight=ft.FontWeight.W_600, color=MUTED)


def helper(text: str) -> ft.Text:
    return ft.Text(text, size=13, color=MUTED)


def note(text: str, bg: str = NOTE_BG) -> ft.Container:
    return ft.Container(
        content=ft.Text(text, size=13, color=INK),
        bgcolor=bg,
        padding=ft.Padding.symmetric(horizontal=12, vertical=12),
        border=ft.Border(left=ft.BorderSide(3, INK if bg == NOTE_BG else "#C9A227")),
    )


def primary_button(label: str, on_click, expand: bool = False, disabled=False):
    return ft.FilledButton(
        content=label,
        bgcolor=INK,
        color=BG,
        height=46,
        expand=expand,
        disabled=disabled,
        on_click=on_click,
    )


def secondary_button(label: str, on_click, expand: bool = False):
    return ft.Button(
        content=label,
        color=INK,
        height=46,
        expand=expand,
        style=ft.ButtonStyle(
            bgcolor=SURFACE,
            side=ft.BorderSide(1, BORDER),
            shape=ft.RoundedRectangleBorder(radius=RADIUS),
        ),
        on_click=on_click,
    )


def text_button(label: str, on_click):
    return ft.TextButton(
        content=ft.Text(label, size=13, color=INK),
        style=ft.ButtonStyle(
            overlay_color=ft.Colors.TRANSPARENT,
            padding=ft.Padding.symmetric(horizontal=0, vertical=4),
        ),
        on_click=on_click,
    )


def logo() -> ft.Row:
    return ft.Row(
        spacing=6,
        controls=[
            ft.Container(
                content=ft.Text("FS", size=10, weight=ft.FontWeight.BOLD, color=BG),
                bgcolor=INK,
                border_radius=3,
                width=18,
                height=18,
                alignment=ft.Alignment.CENTER,
            ),
            ft.Text("FlowShelter", size=14, weight=ft.FontWeight.W_600, color=INK),
        ],
    )
