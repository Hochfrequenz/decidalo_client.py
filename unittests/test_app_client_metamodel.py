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
