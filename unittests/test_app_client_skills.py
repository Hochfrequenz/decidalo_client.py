"""Tests for SkillsDomain."""

from __future__ import annotations

import json

import pytest
from aioresponses import aioresponses

from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.models.skills import SkillAutocomplete, SkillCategory, SkillLevel

BASE_URL = "https://api.decidalo.app"
TOKEN = "test-token"


class TestSkillsAutocomplete:
    async def test_returns_skill_list(self, mock_aiohttp: aioresponses) -> None:
        payload = [{"skillId": 21873, "skillName": "Python", "categoryName": "IT Skills",
                    "languageID": 7, "alreadyUsed": False}]
        mock_aiohttp.get(f"{BASE_URL}/api/Skill/AutocompleteSkill?pattern=Py&useClientLanguage=false&showMoreResults=false&onlyCoreSkills=false", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.skills.autocomplete(pattern="Py")
        assert len(result) == 1
        assert isinstance(result[0], SkillAutocomplete)
        assert result[0].skillId == 21873


class TestSkillsGetLevels:
    async def test_returns_skill_levels(self, mock_aiohttp: aioresponses) -> None:
        payload = [{"skillLevelID": 1, "displayName": "Grundkenntnisse",
                    "description": "Beginner", "numericalValue": 1}]
        mock_aiohttp.get(f"{BASE_URL}/api/Skill/SkillLevels", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.skills.get_levels()
        assert len(result) == 1
        assert isinstance(result[0], SkillLevel)
        assert result[0].numericalValue == 1


class TestSkillsGetCategories:
    async def test_returns_categories(self, mock_aiohttp: aioresponses) -> None:
        payload = [{"categoryId": 4157, "categoryName": "Apple",
                    "parentCategoryId": None, "parentCategoryName": None}]
        mock_aiohttp.get(f"{BASE_URL}/api/Skill/Categories", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.skills.get_categories()
        assert len(result) == 1
        assert isinstance(result[0], SkillCategory)
        assert result[0].categoryName == "Apple"
