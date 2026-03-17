"""Tests for ProfileDomain."""

from __future__ import annotations

import json

import pytest
from aioresponses import aioresponses

from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.models.profile import (
    CoreCompetency,
    ProfileCertificate,
    ProfileHeader,
    ProfileIndustrySection,
    ProfileLanguageSection,
    ProfileRolesSection,
)

BASE_URL = "https://api.decidalo.app"
TOKEN = "test-token"
USER_ID = 155


class TestProfileGetHeader:
    async def test_returns_profile_header(self, mock_aiohttp: aioresponses) -> None:
        payload = {
            "avatarImageUrl": "https://example.com/avatar.jpg",
            "viewMetamodelResult": [
                {"columnName": "FirstName", "columnID": 1, "data": "Max", "label": "Vorname"}
            ],
            "lastEditor": "Admin",
            "lastEditDate": "2026-02-10T10:34:40.417Z",
            "approvedBy": None,
            "approvalDate": None,
            "canBeApproved": True,
            "profileQuality": 3,
        }
        mock_aiohttp.get(f"{BASE_URL}/api/Profile/{USER_ID}/Header", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.profile.get_header(user_id=USER_ID)
        assert isinstance(result, ProfileHeader)
        assert result.avatarImageUrl == "https://example.com/avatar.jpg"
        assert result.profileQuality == 3
        assert len(result.viewMetamodelResult) == 1


class TestProfileGetCertificates:
    async def test_returns_certificate_list(self, mock_aiohttp: aioresponses) -> None:
        payload = [
            {"userCertificateID": 86, "certificateID": 124,
             "certificateName": "SAP Certified", "standardCertificateID": None,
             "issueMonth": 1, "issueYear": 2018, "issuerOrganizationName": "",
             "expirationMonth": None, "expirationYear": None, "credentialUrl": None}
        ]
        mock_aiohttp.get(f"{BASE_URL}/api/Profile/{USER_ID}/Certificates", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.profile.get_certificates(user_id=USER_ID)
        assert len(result) == 1
        assert isinstance(result[0], ProfileCertificate)
        assert result[0].certificateName == "SAP Certified"


class TestProfileGetLanguages:
    async def test_returns_language_section(self, mock_aiohttp: aioresponses) -> None:
        payload = {
            "languages": [{"standardLanguageID": 1, "name": "Deutsch", "languageLevelID": 6}],
            "suggestedLanguages": [],
            "languageLevels": [{"languageLevelID": 1, "displayName": "Grundkenntnisse", "numericalValue": 1}],
        }
        mock_aiohttp.get(f"{BASE_URL}/api/Profile/{USER_ID}/LanguageSection", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.profile.get_languages(user_id=USER_ID)
        assert isinstance(result, ProfileLanguageSection)
        assert len(result.languages) == 1
        assert result.languages[0].name == "Deutsch"


class TestProfileGetCoreCompetencies:
    async def test_returns_competency_list(self, mock_aiohttp: aioresponses) -> None:
        payload = [{"coreCompetencyID": "348", "displayText": "Effektive Kommunikation"}]
        mock_aiohttp.get(f"{BASE_URL}/api/Profile/{USER_ID}/CoreCompetencies", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.profile.get_core_competencies(user_id=USER_ID)
        assert len(result) == 1
        assert isinstance(result[0], CoreCompetency)
        assert result[0].displayText == "Effektive Kommunikation"
