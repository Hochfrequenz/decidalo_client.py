"""Certificates domain client."""

from __future__ import annotations

import json
from typing import Any

from pydantic import TypeAdapter

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.models.certificates import (
    CertificateAutocomplete,
    CertificateHoldersResponse,
)


class CertsDomain:
    """Methods for querying certificates and their holders."""

    def __init__(self, http: HttpHelper) -> None:
        self._http = http

    async def autocomplete(self, pattern: str = "", *, count: int = 5) -> list[CertificateAutocomplete]:
        """Autocomplete certificate names."""
        response_text = await self._http.get(
            "/api/Certificates/Autocomplete", params={"pattern": pattern, "count": str(count)}
        )
        adapter = TypeAdapter(list[CertificateAutocomplete])
        return adapter.validate_json(response_text)

    async def get_holders(
        self, certificate_id: int, *, page_size: int = 20, page_index: int = 0
    ) -> CertificateHoldersResponse:
        """Get all users who hold a specific certificate."""
        response_text = await self._http.get(
            f"/api/Certificates/{certificate_id}/CertificateHolders",
            params={"pageSize": str(page_size), "pageIndex": str(page_index)},
        )
        return CertificateHoldersResponse.model_validate_json(response_text)

    async def get(self, certificate_id: int) -> str:
        """Get certificate detail (uses viewMetamodelResult pattern). Returns raw JSON."""
        return await self._http.get(f"/api/Certificates/{certificate_id}")

    async def get_grid(self, data: dict[str, Any] | None = None) -> str:
        """Get paginated certificate grid. Returns raw JSON."""
        return await self._http.post("/api/Certificates/GetCertificates", data=json.dumps(data or {}))
