"""Skills domain client."""
from __future__ import annotations
from decidalo_app_client._http import HttpHelper

class SkillsDomain:
    def __init__(self, http: HttpHelper) -> None:
        self._http = http

    async def get_levels(self) -> list[object]:
        """Stub for auto-refresh tests."""
        import json
        return json.loads(await self._http.get("/api/Skill/SkillLevels"))
