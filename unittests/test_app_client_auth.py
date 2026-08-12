"""Auth manual verification steps for decidalo_app_client.

Device Code Flow and Token Refresh cannot be tested without a live OIDC server.
The source module src/decidalo_app_client/auth.py is excluded from automated
coverage via the workflow --omit flag; this test file is only covered by the
blanket unittests/* omit entry.

MANUAL VERIFICATION STEPS
--------------------------
1. Install the test dependencies: uv sync --group tests

2. Device Code Flow:
   import asyncio
   from decidalo_app_client.auth import DecidaloAuth
   token = asyncio.run(DecidaloAuth.device_code_login())
   # Expected: prints "Open https://... and enter code XXXX" — complete in browser
   # Expected: returns TokenResponse with access_token, refresh_token, expires_at

3. Refresh Token Flow:
   import asyncio
   from decidalo_app_client.auth import DecidaloAuth
   new_token = asyncio.run(DecidaloAuth.refresh(refresh_token=token.refresh_token))
   # Expected: returns new TokenResponse without browser interaction

4. Client with TokenResponse:
   import asyncio
   from decidalo_app_client import DecidaloAppClient
   async def test():
       async with DecidaloAppClient(token=token) as client:
           levels = await client.skills.get_levels()
           print(levels)
   asyncio.run(test())
   # Expected: returns list of SkillLevel objects

5. Auto-refresh:
   from datetime import datetime, timezone
   from decidalo_app_client.auth import TokenResponse
   expired = TokenResponse(
       access_token=token.access_token,
       refresh_token=token.refresh_token,
       expires_at=datetime(2020, 1, 1, tzinfo=timezone.utc),  # already expired
   )
   # Expected: DecidaloAppClient auto-refreshes on first request
"""
