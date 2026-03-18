"""Skills domain client."""

from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.models.skills import SkillAutocomplete, SkillCategory, SkillLevel


class SkillsDomain:
    """Methods for querying skills, categories, levels, and assessments."""

    def __init__(self, http: HttpHelper) -> None:
        self._http = http

    async def autocomplete(
        self,
        pattern: str = "",
        *,
        use_client_language: bool = False,
        show_more_results: bool = False,
        only_core_skills: bool = False,
    ) -> list[SkillAutocomplete]:
        """Autocomplete skill names by pattern."""
        params = {
            "pattern": pattern,
            "useClientLanguage": str(use_client_language).lower(),
            "showMoreResults": str(show_more_results).lower(),
            "onlyCoreSkills": str(only_core_skills).lower(),
        }
        response_text = await self._http.get("/api/Skill/AutocompleteSkill", params=params)
        adapter = TypeAdapter(list[SkillAutocomplete])
        return adapter.validate_json(response_text)

    async def get_levels(self) -> list[SkillLevel]:
        """Get all skill level definitions (typically 4: Novice to Expert)."""
        response_text = await self._http.get("/api/Skill/SkillLevels")
        adapter = TypeAdapter(list[SkillLevel])
        return adapter.validate_json(response_text)

    async def get_categories(self) -> list[SkillCategory]:
        """Get all skill categories (typically ~328 entries)."""
        response_text = await self._http.get("/api/Skill/Categories")
        adapter = TypeAdapter(list[SkillCategory])
        return adapter.validate_json(response_text)

    async def get_mappings(self, skill_id: int) -> str:
        """Get synonyms/mappings for a skill. Returns raw JSON (response shape unconfirmed)."""
        return await self._http.get(f"/api/Skill/Mappings/{skill_id}")

    async def get_assessments(self, data: dict[str, Any] | None = None) -> str:
        """Get skill assessment matrix. Returns raw JSON.

        The default body returns all skills and users. Filter via:
            {"skillIds": [], "userIds": [175], "teamIDs": [47], "pageIndex": 0, "pageSize": 25}
        skillIds is a filter on which skills to include in the matrix columns (empty = all).
        """
        default = {"skillIds": [], "pageIndex": 0, "pageSize": 25, "teamIDs": [], "userIds": []}
        return await self._http.post("/api/SkillLists/Assessments", data=json.dumps(data or default))

    async def get_grid(self, data: dict[str, Any] | None = None) -> str:
        """Get paginated skill grid. Returns raw JSON."""
        return await self._http.post("/api/Skill/Grid", data=json.dumps(data or {}))

    async def get_lists(self) -> str:
        """Get predefined skill lists. Returns raw JSON."""
        return await self._http.get("/api/SkillLists")
