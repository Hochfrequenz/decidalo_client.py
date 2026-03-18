"""Tests for SearchDomain."""

from __future__ import annotations

import json

from aioresponses import aioresponses

from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.models.search import GlobalSearchResponse, UserForAutocomplete

BASE_URL = "https://api.decidalo.app"
TOKEN = "test-token"


class TestSearchFindPeople:
    async def test_returns_global_search_response(self, mock_aiohttp: aioresponses) -> None:
        payload = {
            "usersWithMatchedQualities": [
                {
                    "userId": 278,
                    "userData": {"displayName": "Jan Gharib", "jobPosition": "Consultant"},
                    "highlights": [],
                    "score": 0.9,
                    "matchedSkills": [],
                    "matchedCertificates": [],
                    "languages": [],
                    "industries": [],
                    "statusInResourceRequest": None,
                }
            ],
            "keywordsWithSynonyms": [
                {
                    "keyword": "SAP",
                    "skillWithSynonyms": [],
                    "certificateWithSynonyms": [],
                    "languages": [],
                    "industries": [],
                }
            ],
            "globalSearchSessionID": 42,
        }
        mock_aiohttp.post(f"{BASE_URL}/api/Search/GlobalSearch", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.search.find_people(keywords=["SAP"])
        assert isinstance(result, GlobalSearchResponse)
        assert len(result.usersWithMatchedQualities) == 1
        assert result.globalSearchSessionID == 42

    async def test_find_people_with_date_range(self, mock_aiohttp: aioresponses) -> None:
        payload = {"usersWithMatchedQualities": [], "keywordsWithSynonyms": [], "globalSearchSessionID": 1}
        mock_aiohttp.post(f"{BASE_URL}/api/Search/GlobalSearch", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.search.find_people(keywords=["SAP"], start_date="2026-01-01", end_date="2026-12-31")
        assert result.usersWithMatchedQualities == []


class TestSearchAutocompleteUser:
    async def test_returns_list_of_users(self, mock_aiohttp: aioresponses) -> None:
        payload = [
            {
                "userID": 278,
                "displayName": "Jan Gharib",
                "jobPosition": "Consultant",
                "lastVisited": "2026-03-05T17:48:37.527Z",
                "imageUrl": None,
                "creatorID": 154,
                "isAlreadyAdded": None,
            }
        ]
        mock_aiohttp.get(
            f"{BASE_URL}/api/Search/GetSearchUsersForAutocomplete?pattern=Jan", body=json.dumps(payload), status=200
        )
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.search.autocomplete_user(pattern="Jan")
        assert len(result) == 1
        assert isinstance(result[0], UserForAutocomplete)
        assert result[0].displayName == "Jan Gharib"
