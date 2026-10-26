"""Flow Shelter API client.

Wraps the endpoints documented in backend/docs/integration.md. All methods are
async; run them from UI handlers with `page.run_task(...)` or from async setup
code with `await`.
"""

import os

import flet as ft
import httpx

TOKEN_KEY = "access_token"


class ApiError(Exception):
    def __init__(self, status: int, body):
        self.status = status
        self.body = body
        super().__init__(f"HTTP {status}: {body}")


class Unauthenticated(ApiError):
    pass


class Api:
    def __init__(self, base_url: str | None = None):
        self.base_url = (
            base_url
            or os.environ.get("FLOWSHELTER_API_URL")
            or "http://127.0.0.1:8000"
        ).rstrip("/")
        self._token: str | None = None
        self._prefs: ft.SharedPreferences | None = None

    # ---- token lifecycle -------------------------------------------------
    async def load_token(self, prefs: ft.SharedPreferences) -> str | None:
        """Restore a saved token on app start."""
        self._prefs = prefs
        self._token = await prefs.get(TOKEN_KEY)
        return self._token

    async def _store_token(self, token: str) -> None:
        self._token = token
        if self._prefs is not None:
            await self._prefs.set(TOKEN_KEY, token)

    async def clear_token(self) -> None:
        self._token = None
        if self._prefs is not None:
            await self._prefs.remove(TOKEN_KEY)

    @property
    def is_authenticated(self) -> bool:
        return self._token is not None

    # ---- HTTP ------------------------------------------------------------
    async def _request(self, method: str, path: str, **kwargs):
        headers = kwargs.pop("headers", {})
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method, f"{self.base_url}{path}", headers=headers, **kwargs
            )

        if response.status_code in (401, 403):
            raise Unauthenticated(response.status_code, _error_body(response))
        if response.status_code >= 400:
            raise ApiError(response.status_code, _error_body(response))
        if response.status_code == 204:
            return None
        return response.json()

    # ---- auth ------------------------------------------------------------
    async def register(self, name: str, email: str, password: str) -> dict:
        return await self._request(
            "POST",
            "/auth/register",
            json={"name": name, "email": email, "password": password},
        )

    async def login(self, email: str, password: str) -> dict:
        data = await self._request(
            "POST", "/auth/login", json={"email": email, "password": password}
        )
        await self._store_token(data["access_token"])
        return data

    async def me(self) -> dict:
        return await self._request("GET", "/auth/me")

    # ---- onboarding ------------------------------------------------------
    async def get_onboarding(self) -> dict:
        return await self._request("GET", "/api/onboarding")

    async def patch_onboarding(self, **sections) -> dict:
        """Send only the sections given: financial_profile, financial_balance,
        expected_incomes, savings_goals."""
        return await self._request(
            "PATCH", "/api/onboarding", json=_drop_empty(sections)
        )

    async def set_step(self, step: int) -> dict:
        return await self._request(
            "PUT", "/api/onboarding/step", json={"current_step": step}
        )

    async def complete_onboarding(self) -> dict:
        return await self._request("POST", "/api/onboarding/complete")

    async def get_commitments(self) -> dict:
        return await self._request("GET", "/api/onboarding/commitments")

    async def save_commitments(self, commitments: list[dict]) -> dict:
        return await self._request(
            "PUT", "/api/onboarding/commitments", json={"commitments": commitments}
        )

    # ---- dashboard -------------------------------------------------------
    async def overview(self) -> dict:
        return await self._request("GET", "/api/dashboard/overview")

    async def alerts(self) -> list:
        return await self._request("GET", "/api/dashboard/alerts")

    async def upcoming(self) -> dict:
        return await self._request("GET", "/api/dashboard/upcoming")


def _drop_empty(value):
    """Remove None and blank entries recursively, so optional fields are left
    out of the request instead of being sent as null."""

    if isinstance(value, dict):
        return {
            k: _drop_empty(v)
            for k, v in value.items()
            if v is not None and not (isinstance(v, str) and not v.strip())
        }
    if isinstance(value, list):
        return [_drop_empty(v) for v in value]
    return value


def _error_body(response: httpx.Response):
    try:
        return response.json()
    except ValueError:
        return response.text


def save_date(d) -> str | None:
    """Pass through an ISO string; dates are sent as YYYY-MM-DD."""
    if not d:
        return None
    return d.isoformat() if hasattr(d, "isoformat") else str(d)


def error_message(exc: Exception) -> str:
    """Turn an ApiError into something worth showing a user."""

    if isinstance(exc, httpx.ConnectError):
        return "Can't reach the Flow Shelter server. Check your connection."
    if isinstance(exc, httpx.TimeoutException):
        return "The server took too long to respond. Try again."
    if isinstance(exc, ApiError):
        body = exc.body
        if isinstance(body, dict):
            detail = body.get("detail")
            if isinstance(detail, str):
                return detail
            if isinstance(detail, dict) and detail.get("message"):
                return detail["message"]
            if isinstance(detail, list) and detail:
                first = detail[0]
                field = ".".join(str(p) for p in first.get("loc", [])[1:])
                return f"{field.replace('_', ' ').capitalize()}: {first.get('msg', 'invalid')}"
        return f"Something went wrong ({exc.status})."
    return "Something went wrong. Please try again."
