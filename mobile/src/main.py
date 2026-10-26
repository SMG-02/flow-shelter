"""Entry point: `python src/main.py` (or `flet run src/main.py`).

The API base URL comes from FLOWSHELTER_API_URL, defaulting to
http://127.0.0.1:8000 where the FastAPI backend runs locally.
"""

import flet as ft

from app import FlowShelterApp


def main(page: ft.Page):
    app = FlowShelterApp(page)
    page.run_task(app.start)


if __name__ == "__main__":
    ft.run(main)
