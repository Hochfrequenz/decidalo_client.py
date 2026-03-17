"""Tests for RolesDomain."""

from __future__ import annotations

import json

import pytest
from aioresponses import aioresponses

from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.models.roles import Role, RoleCertCheck, RoleSkillCheck

BASE_URL = "https://api.decidalo.app"
TOKEN = "test-token"
ROLE_ID = 18
USER_ID = 155


class TestRolesGet:
    async def test_returns_role(self, mock_aiohttp: aioresponses) -> None:
        payload = {"roleID": 18, "roleSkillsCount": 0, "roleCertificatesCount": 0,
                   "roleName": "Business-Analyst", "description": "...", "redesignRoleID": 12103,
                   "creatorID": 154, "roleCode": None}
        mock_aiohttp.get(f"{BASE_URL}/api/Role/{ROLE_ID}", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.roles.get(role_id=ROLE_ID)
        assert isinstance(result, Role)
        assert result.roleID == 18
        assert result.roleName == "Business-Analyst"


class TestRolesCheckUserSkills:
    async def test_returns_skill_check(self, mock_aiohttp: aioresponses) -> None:
        payload = {"isFulfilled": True, "matchedUserSkillRoles": [], "missingRoleSkills": []}
        mock_aiohttp.get(f"{BASE_URL}/api/Role/{ROLE_ID}/User/{USER_ID}/Skills",
                         body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.roles.check_user_skills(role_id=ROLE_ID, user_id=USER_ID)
        assert isinstance(result, RoleSkillCheck)
        assert result.isFulfilled is True


class TestRolesCheckUserCertificates:
    async def test_returns_cert_check(self, mock_aiohttp: aioresponses) -> None:
        payload = {"isFulfilled": False, "matchedUserRoleCertificates": [], "missingUserRoleCertificates": []}
        mock_aiohttp.get(f"{BASE_URL}/api/Role/{ROLE_ID}/User/{USER_ID}/Certificates",
                         body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.roles.check_user_certificates(role_id=ROLE_ID, user_id=USER_ID)
        assert isinstance(result, RoleCertCheck)
        assert result.isFulfilled is False
