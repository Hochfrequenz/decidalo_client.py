"""Tests for TeamsDomain."""

from __future__ import annotations

import json

from aioresponses import aioresponses

from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.models.teams import SimpleTeamMember, TeamDetails

BASE_URL = "https://api.decidalo.app"
TOKEN = "test-token"
TEAM_ID = 47


class TestTeamsGetDetails:
    async def test_returns_team_details(self, mock_aiohttp: aioresponses) -> None:
        payload = {
            "teamID": 47,
            "teamName": "2.2.2",
            "parentTeamID": 37,
            "teamManager": {
                "teamMemberID": 175,
                "teamMemberName": "Max Muster",
                "teamMemberPosition": "Manager",
                "avatarURL": None,
                "substituteID": None,
            },
            "additionalManagers": [],
            "teamMembers": [],
        }
        mock_aiohttp.get(f"{BASE_URL}/api/Teams/{TEAM_ID}/TeamDetails", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.teams.get_details(team_id=TEAM_ID)
        assert isinstance(result, TeamDetails)
        assert result.teamID == 47
        assert result.teamName == "2.2.2"
        assert result.teamManager.teamMemberName == "Max Muster"


class TestTeamsGetMembersUnderCurrentUser:
    async def test_returns_simple_member_list(self, mock_aiohttp: aioresponses) -> None:
        payload = [{"userId": 159, "displayName": "Jonas Schneegans"}, {"userId": 276, "displayName": "Timon Beck"}]
        mock_aiohttp.get(f"{BASE_URL}/api/Teams/TeamMembersUnderCurrentUser", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.teams.get_members_under_current_user()
        assert len(result) == 2
        assert isinstance(result[0], SimpleTeamMember)
        assert result[0].displayName == "Jonas Schneegans"
