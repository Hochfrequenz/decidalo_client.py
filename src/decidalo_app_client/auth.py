"""Authentication helpers for the Decidalo App API.

Device Code Flow and Refresh Token flow for login.decidalo.app (IdentityServer4 + Microsoft SSO).
Note: Device Code Flow requires manual testing against a live OIDC server.
This module is excluded from automated test coverage.
"""

# pylint: disable=import-outside-toplevel
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """OAuth2 token response from login.decidalo.app."""

    access_token: str
    refresh_token: str | None = None
    expires_at: datetime  # UTC datetime

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """Return True if the token expires within buffer_seconds."""
        now = datetime.now(timezone.utc)
        return (self.expires_at - now).total_seconds() < buffer_seconds


class DecidaloAuth:
    """OAuth2 authentication flows for the Decidalo App API.

    OIDC provider: https://login.decidalo.app
    Client ID: decidalo.client
    Scopes: openid decidalohostapi.full client user offline_access
    """

    AUTHORITY = "https://login.decidalo.app"
    CLIENT_ID = "decidalo.client"
    SCOPES = ["openid", "decidalohostapi.full", "client", "user", "offline_access"]

    @classmethod
    async def device_code_login(cls) -> TokenResponse:
        """Acquire a token via Device Code Flow (interactive, browser required).

        Prints the device code and URL to stdout. Blocks until the user completes login.
        Store the returned refresh_token securely for subsequent headless use.

        Raises:
            AppAuthError: If the device code flow fails.
        """
        import asyncio

        import msal

        from decidalo_app_client.exceptions import AppAuthError

        app = msal.PublicClientApplication(cls.CLIENT_ID, authority=cls.AUTHORITY)
        flow = await asyncio.to_thread(app.initiate_device_flow, cls.SCOPES)
        if "user_code" not in flow:
            raise AppAuthError(f"Device code flow failed to initiate: {flow.get('error_description', flow)}")
        print(flow["message"])  # "Open https://... and enter code XXXX-XXXX"
        result = await asyncio.to_thread(app.acquire_token_by_device_flow, flow)
        if "access_token" not in result:
            raise AppAuthError(f"Device code flow failed: {result.get('error_description', result)}")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(result["expires_in"]))
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token"),
            expires_at=expires_at,
        )

    @classmethod
    async def refresh(cls, refresh_token: str) -> TokenResponse:
        """Acquire a new access token using a refresh token (headless).

        Raises:
            AppAuthError: If the refresh fails.
        """
        import asyncio

        import msal

        from decidalo_app_client.exceptions import AppAuthError

        app = msal.PublicClientApplication(cls.CLIENT_ID, authority=cls.AUTHORITY)
        result = await asyncio.to_thread(app.acquire_token_by_refresh_token, refresh_token, cls.SCOPES)
        if "access_token" not in result:
            raise AppAuthError(f"Token refresh failed: {result.get('error_description', result)}")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(result["expires_in"]))
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", refresh_token),
            expires_at=expires_at,
        )
