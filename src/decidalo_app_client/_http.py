"""Shared HTTP helper for the Decidalo App API client."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import aiohttp

from decidalo_app_client.exceptions import AppAPIError, AppAuthError


class HttpHelper:
    """Shared GET/POST helper that injects Bearer auth.

    Owned by DecidaloAppClient. Domain objects hold a reference to this helper.
    Session lifecycle (create/close) is managed by DecidaloAppClient via set_session().
    """

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None
        self._get_token: Callable[[], str] | None = None
        self._ensure_fresh: Callable[[], Awaitable[None]] | None = None

    def set_session(
        self,
        session: aiohttp.ClientSession,
        get_token: Callable[[], str],
        ensure_fresh: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        """Called by DecidaloAppClient.__aenter__ to wire up session and token provider."""
        self._session = session
        self._get_token = get_token
        self._ensure_fresh = ensure_fresh

    def _headers(self) -> dict[str, str]:
        token = self._get_token() if self._get_token else ""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _handle_response(self, response: aiohttp.ClientResponse) -> str:
        text = await response.text()
        if response.status in (401, 403):
            raise AppAuthError(f"Authentication failed ({response.status}): {text}")
        if response.status >= 400:
            raise AppAPIError(status_code=response.status, message=text or f"HTTP {response.status}")
        return text

    async def get(self, path: str, params: dict[str, str] | None = None) -> str:
        """Make a GET request. Raises RuntimeError if called outside context manager."""
        if self._session is None:
            raise RuntimeError("HttpHelper must be used within an async context manager")
        if self._ensure_fresh is not None:
            await self._ensure_fresh()
        url = f"{self._base_url}{path}"
        async with self._session.get(url, headers=self._headers(), params=params) as response:
            return await self._handle_response(response)

    async def post(self, path: str, data: str | None = None) -> str:
        """Make a POST request. Raises RuntimeError if called outside context manager."""
        if self._session is None:
            raise RuntimeError("HttpHelper must be used within an async context manager")
        if self._ensure_fresh is not None:
            await self._ensure_fresh()
        url = f"{self._base_url}{path}"
        async with self._session.post(url, headers=self._headers(), data=data) as response:
            return await self._handle_response(response)
