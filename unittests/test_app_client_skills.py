"""Tests for SkillsDomain."""

from __future__ import annotations

import json

from aioresponses import aioresponses

from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.models.skills import SkillAutocomplete, SkillCategory, SkillLevel

BASE_URL = "https://api.decidalo.app"
TOKEN = "test-token"


class TestSkillsAutocomplete:
    async def test_returns_skill_list(self, mock_aiohttp: aioresponses) -> None:
        payload = [
            {
                "skillId": 21873,
                "skillName": "Python",
                "categoryName": "IT Skills",
                "languageID": 7,
                "alreadyUsed": False,
            }
        ]
        url = f"{BASE_URL}/api/Skill/AutocompleteSkill?pattern=Py&useClientLanguage=false&showMoreResults=false&onlyCoreSkills=false"
        mock_aiohttp.get(url, body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.skills.autocomplete(pattern="Py")
        assert len(result) == 1
        assert isinstance(result[0], SkillAutocomplete)
        assert result[0].skillId == 21873


class TestSkillsGetLevels:
    async def test_returns_skill_levels(self, mock_aiohttp: aioresponses) -> None:
        payload = [
            {"skillLevelID": 1, "displayName": "Grundkenntnisse", "description": "Beginner", "numericalValue": 1}
        ]
        mock_aiohttp.get(f"{BASE_URL}/api/Skill/SkillLevels", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.skills.get_levels()
        assert len(result) == 1
        assert isinstance(result[0], SkillLevel)
        assert result[0].numericalValue == 1


class TestSkillsGetCategories:
    async def test_returns_categories(self, mock_aiohttp: aioresponses) -> None:
        payload = [{"categoryId": 4157, "categoryName": "Apple", "parentCategoryId": None, "parentCategoryName": None}]
        mock_aiohttp.get(f"{BASE_URL}/api/Skill/Categories", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.skills.get_categories()
        assert len(result) == 1
        assert isinstance(result[0], SkillCategory)
        assert result[0].categoryName == "Apple"


class TestSkillsGetAssessments:
    async def test_sends_default_body_and_returns_json(self, mock_aiohttp: aioresponses) -> None:
        payload = {"skills": [], "users": [], "assessments": []}
        mock_aiohttp.post(f"{BASE_URL}/api/SkillLists/Assessments", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.skills.get_assessments()
        assert '"skills"' in result

    async def test_accepts_custom_body(self, mock_aiohttp: aioresponses) -> None:
        payload = {"skills": [], "users": [], "assessments": []}
        mock_aiohttp.post(f"{BASE_URL}/api/SkillLists/Assessments", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.skills.get_assessments({"skillIds": [], "teamIDs": [47], "pageIndex": 0, "pageSize": 25, "userIds": []})
        assert result is not None
