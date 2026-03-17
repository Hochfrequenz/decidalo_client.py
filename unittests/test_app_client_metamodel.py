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
