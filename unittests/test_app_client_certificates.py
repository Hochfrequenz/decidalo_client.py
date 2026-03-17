"""Tests for CertsDomain."""

from __future__ import annotations

import json

import pytest
from aioresponses import aioresponses

from decidalo_app_client import DecidaloAppClient
from decidalo_app_client.models.certificates import CertificateAutocomplete, CertificateHoldersResponse

BASE_URL = "https://api.decidalo.app"
TOKEN = "test-token"
CERT_ID = 143


class TestCertificatesAutocomplete:
    async def test_returns_certificate_list(self, mock_aiohttp: aioresponses) -> None:
        payload = [{"certificateID": 120, "certificateName": "Certified ScrumMaster (CSM)"}]
        mock_aiohttp.get(f"{BASE_URL}/api/Certificates/Autocomplete?count=5&pattern=Scrum", body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.certificates.autocomplete(pattern="Scrum")
        assert len(result) == 1
        assert isinstance(result[0], CertificateAutocomplete)
        assert result[0].certificateID == 120


class TestCertificatesGetHolders:
    async def test_returns_holders_response(self, mock_aiohttp: aioresponses) -> None:
        payload = {
            "certificateHolders": [
                {"userID": 155, "displayName": "Max Muster", "expirationMonth": None,
                 "expirationYear": None, "avatarImageUrl": "https://example.com/img.jpg"}
            ],
            "totalCount": 1,
        }
        mock_aiohttp.get(f"{BASE_URL}/api/Certificates/{CERT_ID}/CertificateHolders?pageIndex=0&pageSize=20",
                         body=json.dumps(payload), status=200)
        async with DecidaloAppClient(token=TOKEN) as client:
            result = await client.certificates.get_holders(certificate_id=CERT_ID)
        assert isinstance(result, CertificateHoldersResponse)
        assert result.totalCount == 1
        assert result.certificateHolders[0].displayName == "Max Muster"
