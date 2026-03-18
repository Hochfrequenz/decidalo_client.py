"""Authentication helpers for the Decidalo App API.

Device Code Flow and Refresh Token flow for login.decidalo.app (IdentityServer4 + Microsoft SSO).
Implemented via direct HTTP requests against the OIDC endpoints — no MSAL dependency needed.
Note: Device Code Flow requires manual testing against a live OIDC server.
This module is excluded from automated test coverage.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone

import aiohttp
from pydantic import BaseModel

from decidalo_app_client.exceptions import AppAuthError


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

    OIDC provider: https://login.decidalo.app (IdentityServer4)
    Client ID: decidalo.client
    Scopes: openid decidalohostapi.full client user offline_access
    """

    CLIENT_ID = "decidalo.client"
    SCOPES = "openid decidalohostapi.full client user offline_access"
    DEVICE_AUTH_ENDPOINT = "https://login.decidalo.app/connect/deviceauthorization"
    TOKEN_ENDPOINT = "https://login.decidalo.app/connect/token"

    @classmethod
    async def device_code_login(cls) -> TokenResponse:
        """Acquire a token via Device Code Flow (interactive, browser required).

        Prints the verification URL and user code to stdout.
        Blocks until the user completes login in the browser.
        Store the returned refresh_token securely for subsequent headless use.

        Raises:
            AppAuthError: If the device code flow fails.
        """
        async with aiohttp.ClientSession() as session:
            # Step 1: request device code
            async with session.post(
                cls.DEVICE_AUTH_ENDPOINT,
                data={"client_id": cls.CLIENT_ID, "scope": cls.SCOPES},
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise AppAuthError(f"Device code request failed ({resp.status}): {body}")
                device_data = await resp.json(content_type=None)

            if "user_code" not in device_data:
                raise AppAuthError(f"Device code flow failed to initiate: {device_data}")

            print(f"\nBitte öffne: {device_data['verification_uri_complete']}")
            print(f"Code: {device_data['user_code']}\n")

            # Step 2: poll for token
            interval = int(device_data.get("interval", 5))
            deadline = time.monotonic() + int(device_data.get("expires_in", 300))

            while time.monotonic() < deadline:
                await asyncio.sleep(interval)
                async with session.post(
                    cls.TOKEN_ENDPOINT,
                    data={
                        "client_id": cls.CLIENT_ID,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                        "device_code": device_data["device_code"],
                    },
                ) as token_resp:
                    result = await token_resp.json(content_type=None)

                if "access_token" in result:
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(result["expires_in"]))
                    return TokenResponse(
                        access_token=result["access_token"],
                        refresh_token=result.get("refresh_token"),
                        expires_at=expires_at,
                    )

                error = result.get("error", "")
                if error == "authorization_pending":
                    continue
                if error == "slow_down":
                    interval += 5
                    continue
                raise AppAuthError(f"Device code flow failed: {result.get('error_description', result)}")

        raise AppAuthError("Device code flow timed out.")

    @classmethod
    async def refresh(cls, refresh_token: str) -> TokenResponse:
        """Acquire a new access token using a refresh token (headless).

        Raises:
            AppAuthError: If the refresh fails.
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                cls.TOKEN_ENDPOINT,
                data={
                    "client_id": cls.CLIENT_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "scope": cls.SCOPES,
                },
            ) as resp:
                result = await resp.json(content_type=None)

        if "access_token" not in result:
            raise AppAuthError(f"Token refresh failed: {result.get('error_description', result)}")
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(result["expires_in"]))
        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result.get("refresh_token", refresh_token),
            expires_at=expires_at,
        )
