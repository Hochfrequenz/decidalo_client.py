"""Tests for ProjectsDomain."""

from __future__ import annotations

import json

import pytest
from aioresponses import aioresponses

from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.models.projects import ProjectHeader, ProjectOverview

BASE_URL = "https://api.decidalo.app"
TOKEN = "test-token"
PROJECT_ID = 1462


class TestProjectsGetHeader:
    async def test_returns_project_header(self, mock_aiohttp: aioresponses) -> None:
        payload = {"viewMetamodelResult": [
            {"columnName": "ProjectName", "columnID": 10, "data": "My Project", "label": "Projektname"}
        ]}
        mock_aiohttp.get(f"{BASE_URL}/api/ProjectReference/{PROJECT_ID}/Header",
                         body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.projects.get_header(project_id=PROJECT_ID)
        assert isinstance(result, ProjectHeader)
        assert len(result.viewMetamodelResult) == 1


class TestProjectsGetTeam:
    async def test_returns_empty_list_for_no_members(self, mock_aiohttp: aioresponses) -> None:
        mock_aiohttp.get(f"{BASE_URL}/api/ProjectReference/{PROJECT_ID}/TeamMembers",
                         body="[]", status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.projects.get_team(project_id=PROJECT_ID)
        assert result == []


class TestProjectsGetOverview:
    async def test_returns_project_overview(self, mock_aiohttp: aioresponses) -> None:
        payload = {
            "profileEntries": [],
            "planningStartDate": "2024-01-01T00:00:00Z",
            "planningEndDate": "2027-01-03T00:00:00Z",
            "bookedMembers": [],
            "resourceManager": None,
            "projectManager": None,
            "substituteProjectManager": None,
            "salesResponsible": None,
            "viewMetamodelResult": [],
        }
        mock_aiohttp.get(f"{BASE_URL}/api/ProjectReference/{PROJECT_ID}/Overview",
                         body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.projects.get_overview(project_id=PROJECT_ID)
        assert isinstance(result, ProjectOverview)
        assert result.planningStartDate == "2024-01-01T00:00:00Z"
