"""DecidaloAppClient — async client for the Decidalo App API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import aiohttp

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.auth import DecidaloAuth, TokenResponse
from decidalo_app_client.domains.certificates import CertsDomain
from decidalo_app_client.domains.profile import ProfileDomain
from decidalo_app_client.domains.projects import ProjectsDomain
from decidalo_app_client.domains.roles import RolesDomain
from decidalo_app_client.domains.search import SearchDomain
from decidalo_app_client.domains.skills import SkillsDomain
from decidalo_app_client.domains.teams import TeamsDomain
from decidalo_app_client.exceptions import AppAuthError

if TYPE_CHECKING:
    from types import TracebackType

DEFAULT_BASE_URL = "https://api.decidalo.app"


class DecidaloAppClient:
    """Async client for the Decidalo App API (api.decidalo.app).

    Accepts either a static access token string (no refresh) or a TokenResponse
    (auto-refresh enabled when refresh_token is present).

    Example:
        async with DecidaloAppClient(token="your-bearer-token") as client:
            results = await client.search.find_people(keywords=["SAP"])
    """

    def __init__(
        self,
        token: str | TokenResponse,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        if isinstance(token, str):
            self._static_token: str | None = token
            self._token_response: TokenResponse | None = None
        else:
            self._static_token = None
            self._token_response = token

        self._http = HttpHelper(base_url=base_url)
        self.search = SearchDomain(self._http)
        self.skills = SkillsDomain(self._http)
        self.profile = ProfileDomain(self._http)
        self.projects = ProjectsDomain(self._http)
        self.certificates = CertsDomain(self._http)
        self.roles = RolesDomain(self._http)
        self.teams = TeamsDomain(self._http)

    def _current_token(self) -> str:
        """Return the current access token (does NOT refresh — call _ensure_fresh first)."""
        if self._static_token is not None:
            return self._static_token
        assert self._token_response is not None
        return self._token_response.access_token

    async def _ensure_fresh(self) -> None:
        """Refresh the token if it is expired (or close to expiry). No-op for static tokens."""
        if self._token_response is None:
            return  # static token — no refresh
        if not self._token_response.is_expired():
            return
        if self._token_response.refresh_token is None:
            raise AppAuthError("Access token expired and no refresh_token available.")
        self._token_response = await DecidaloAuth.refresh(self._token_response.refresh_token)

    async def __aenter__(self) -> DecidaloAppClient:
        session = aiohttp.ClientSession()
        self._http.set_session(
            session=session,
            get_token=self._current_token,
            ensure_fresh=self._ensure_fresh,
        )
        self._session = session
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session is not None:
            await self._session.close()
            self._http._session = None
            self._session = None
