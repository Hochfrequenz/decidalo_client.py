"""Tests for decidalo_app_client exceptions and metamodel parsing."""

from __future__ import annotations

import pytest

from decidalo_app_client.exceptions import AppAPIError, AppAuthError


class TestExceptions:
    def test_app_api_error_stores_status_and_message(self) -> None:
        err = AppAPIError(status_code=404, message="Not found")
        assert err.status_code == 404
        assert err.message == "Not found"
        assert "404" in str(err)

    def test_app_auth_error_is_exception(self) -> None:
        err = AppAuthError("token expired")
        assert isinstance(err, Exception)
        assert "token expired" in str(err)

    def test_exceptions_are_independent_of_decidalo_client(self) -> None:
        from decidalo_client.exceptions import DecidaloClientError
        assert not issubclass(AppAPIError, DecidaloClientError)
        assert not issubclass(AppAuthError, DecidaloClientError)


import json
from unittest.mock import AsyncMock, MagicMock
import aiohttp
import pytest
from aioresponses import aioresponses

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.exceptions import AppAPIError, AppAuthError


BASE_URL = "https://api.decidalo.app"
TOKEN = "test-bearer-token"


class TestHttpHelper:
    def _make_helper(self) -> HttpHelper:
        helper = HttpHelper(base_url=BASE_URL)
        session = MagicMock(spec=aiohttp.ClientSession)
        helper.set_session(session=session, get_token=lambda: TOKEN)
        return helper

    async def test_get_returns_response_text(self, mock_aiohttp: aioresponses) -> None:
        mock_aiohttp.get(f"{BASE_URL}/api/test", body='["hello"]', status=200)
        helper = HttpHelper(base_url=BASE_URL)
        async with aiohttp.ClientSession() as session:
            helper.set_session(session=session, get_token=lambda: TOKEN)
            result = await helper.get("/api/test")
        assert result == '["hello"]'

    async def test_get_sends_bearer_token(self, mock_aiohttp: aioresponses) -> None:
        mock_aiohttp.get(f"{BASE_URL}/api/test", body="{}", status=200)
        helper = HttpHelper(base_url=BASE_URL)
        async with aiohttp.ClientSession() as session:
            helper.set_session(session=session, get_token=lambda: TOKEN)
            await helper.get("/api/test")
        calls = list(mock_aiohttp.requests.values())
        assert calls[0][0].kwargs["headers"]["Authorization"] == f"Bearer {TOKEN}"

    async def test_get_401_raises_app_auth_error(self, mock_aiohttp: aioresponses) -> None:
        mock_aiohttp.get(f"{BASE_URL}/api/test", body="Unauthorized", status=401)
        helper = HttpHelper(base_url=BASE_URL)
        async with aiohttp.ClientSession() as session:
            helper.set_session(session=session, get_token=lambda: TOKEN)
            with pytest.raises(AppAuthError):
                await helper.get("/api/test")

    async def test_get_404_raises_app_api_error(self, mock_aiohttp: aioresponses) -> None:
        mock_aiohttp.get(f"{BASE_URL}/api/test", body="Not found", status=404)
        helper = HttpHelper(base_url=BASE_URL)
        async with aiohttp.ClientSession() as session:
            helper.set_session(session=session, get_token=lambda: TOKEN)
            with pytest.raises(AppAPIError) as exc_info:
                await helper.get("/api/test")
        assert exc_info.value.status_code == 404

    async def test_post_sends_json_body(self, mock_aiohttp: aioresponses) -> None:
        mock_aiohttp.post(f"{BASE_URL}/api/test", body='{"ok": true}', status=200)
        helper = HttpHelper(base_url=BASE_URL)
        async with aiohttp.ClientSession() as session:
            helper.set_session(session=session, get_token=lambda: TOKEN)
            result = await helper.post("/api/test", data='{"key": "value"}')
        assert result == '{"ok": true}'

    async def test_get_without_session_raises_runtime_error(self) -> None:
        helper = HttpHelper(base_url=BASE_URL)
        with pytest.raises(RuntimeError, match="context manager"):
            await helper.get("/api/test")


from decidalo_app_client import DecidaloAppClient


class TestDecidaloAppClientContextManager:
    async def test_aenter_creates_session(self) -> None:
        async with DecidaloAppClient(token="abc") as client:
            assert client._http._session is not None

    async def test_aexit_closes_session(self) -> None:
        client = DecidaloAppClient(token="abc")
        async with client:
            pass
        assert client._http._session is None

    async def test_domains_are_accessible(self) -> None:
        async with DecidaloAppClient(token="abc") as client:
            from decidalo_app_client.domains.search import SearchDomain
            from decidalo_app_client.domains.skills import SkillsDomain
            from decidalo_app_client.domains.profile import ProfileDomain
            from decidalo_app_client.domains.projects import ProjectsDomain
            from decidalo_app_client.domains.certificates import CertsDomain
            from decidalo_app_client.domains.roles import RolesDomain
            from decidalo_app_client.domains.teams import TeamsDomain
            assert isinstance(client.search, SearchDomain)
            assert isinstance(client.skills, SkillsDomain)
            assert isinstance(client.profile, ProfileDomain)
            assert isinstance(client.projects, ProjectsDomain)
            assert isinstance(client.certificates, CertsDomain)
            assert isinstance(client.roles, RolesDomain)
            assert isinstance(client.teams, TeamsDomain)

    async def test_str_token_disables_refresh(self) -> None:
        client = DecidaloAppClient(token="static-token")
        assert client._token_response is None
        assert client._static_token == "static-token"

    async def test_token_response_enables_refresh(self) -> None:
        from datetime import datetime, timezone
        from decidalo_app_client.auth import TokenResponse
        tr = TokenResponse(
            access_token="abc",
            refresh_token="refresh-xyz",
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        client = DecidaloAppClient(token=tr)
        assert client._token_response is tr
        assert client._static_token is None


class TestDecidaloAppClientAutoRefresh:
    async def test_expired_token_triggers_refresh(self, mock_aiohttp: aioresponses) -> None:
        """Auto-refresh is called before a request when the token is expired."""
        from datetime import datetime, timezone
        from unittest.mock import AsyncMock, patch
        from decidalo_app_client.auth import TokenResponse, DecidaloAuth

        expired = TokenResponse(
            access_token="old-token",
            refresh_token="valid-refresh",
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),  # already expired
        )
        fresh = TokenResponse(
            access_token="new-token",
            refresh_token="new-refresh",
            expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
        )
        mock_aiohttp.get(f"https://api.decidalo.app/api/Skill/SkillLevels", body="[]", status=200)

        with patch.object(DecidaloAuth, "refresh", new=AsyncMock(return_value=fresh)) as mock_refresh:
            async with DecidaloAppClient(token=expired) as client:
                await client.skills.get_levels()
            mock_refresh.assert_awaited_once_with("valid-refresh")

    async def test_static_token_never_refreshes(self, mock_aiohttp: aioresponses) -> None:
        """Static str token never triggers refresh even if it would be expired."""
        from unittest.mock import AsyncMock, patch
        from decidalo_app_client.auth import DecidaloAuth

        mock_aiohttp.get(f"https://api.decidalo.app/api/Skill/SkillLevels", body="[]", status=200)

        with patch.object(DecidaloAuth, "refresh", new=AsyncMock()) as mock_refresh:
            async with DecidaloAppClient(token="static-forever") as client:
                await client.skills.get_levels()
            mock_refresh.assert_not_awaited()

    async def test_expired_token_without_refresh_token_raises(self) -> None:
        """If token is expired and no refresh_token is available, AppAuthError is raised."""
        from datetime import datetime, timezone
        from decidalo_app_client.auth import TokenResponse
        from decidalo_app_client.exceptions import AppAuthError

        expired = TokenResponse(
            access_token="old-token",
            refresh_token=None,  # no refresh token
            expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        async with DecidaloAppClient(token=expired) as client:
            with pytest.raises(AppAuthError, match="refresh_token"):
                await client.skills.get_levels()


from decidalo_app_client.models.metamodel import EntityColumn, MetamodelColumn, resolve_row


class TestResolveRow:
    def _make_columns(self) -> list[EntityColumn]:
        return [
            EntityColumn(
                viewMetamodelEntryID=181,
                column=MetamodelColumn(columnName="StartDate"),
            ),
            EntityColumn(
                viewMetamodelEntryID=221,
                column=MetamodelColumn(columnName="EndDate"),
            ),
            EntityColumn(
                viewMetamodelEntryID=27,
                column=MetamodelColumn(columnName="ProjectName"),
            ),
        ]

    def test_resolves_known_keys(self) -> None:
        columns = self._make_columns()
        row = {"181": "2024-01-01", "221": "2024-12-31", "27": "Projekt XYZ"}
        result = resolve_row(columns, row)
        assert result == {"StartDate": "2024-01-01", "EndDate": "2024-12-31", "ProjectName": "Projekt XYZ"}

    def test_raises_on_unknown_key(self) -> None:
        columns = self._make_columns()
        row = {"181": "2024-01-01", "999": "unexpected"}
        with pytest.raises(KeyError):
            resolve_row(columns, row)

    def test_empty_row_returns_empty_dict(self) -> None:
        columns = self._make_columns()
        assert resolve_row(columns, {}) == {}

    def test_negative_key_resolves_if_in_columns(self) -> None:
        columns = [EntityColumn(viewMetamodelEntryID=-8, column=MetamodelColumn(columnName="ID"))]
        row = {"-8": "42"}
        assert resolve_row(columns, row) == {"ID": "42"}
