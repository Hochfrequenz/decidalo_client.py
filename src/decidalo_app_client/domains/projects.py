"""Projects domain client."""

from __future__ import annotations

import json
from typing import Any, cast

from pydantic import TypeAdapter

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.models.metamodel import EntityColumn, MetamodelGrid, resolve_row
from decidalo_app_client.models.projects import (
    ProjectDetails,
    ProjectHeader,
    ProjectOverview,
    ProjectTeamMember,
)


class ProjectsDomain:
    """Methods for querying project references and team members."""

    def __init__(self, http: HttpHelper) -> None:
        self._http = http

    async def get_header(self, project_id: int) -> ProjectHeader:
        """Get project header (uses viewMetamodelResult pattern)."""
        response_text = await self._http.get(f"/api/ProjectReference/{project_id}/Header")
        return ProjectHeader.model_validate_json(response_text)

    async def get_overview(self, project_id: int) -> ProjectOverview:
        """Get project overview including profile entries and dates."""
        response_text = await self._http.get(f"/api/ProjectReference/{project_id}/Overview")
        return ProjectOverview.model_validate_json(response_text)

    async def get_details(self, project_id: int) -> ProjectDetails:
        """Get project details (uses viewMetamodelResult pattern)."""
        response_text = await self._http.get(f"/api/ProjectReference/{project_id}/Details")
        return ProjectDetails.model_validate_json(response_text)

    async def get_team(self, project_id: int) -> list[ProjectTeamMember]:
        """Get all team members on a project."""
        response_text = await self._http.get(f"/api/ProjectReference/{project_id}/TeamMembers")
        adapter = TypeAdapter(list[ProjectTeamMember])
        return adapter.validate_json(response_text)

    async def get_contacts(self, project_id: int) -> list[Any]:
        """Get project contacts. Returns raw list (shape only observed as empty in HAR)."""
        return cast(list[Any], json.loads(await self._http.get(f"/api/ProjectReference/{project_id}/ProjectContacts")))

    async def get_all_team_members_for_user(self, user_id: int) -> list[Any]:
        """Get all projects + members visible to a user."""
        return cast(
            list[Any],
            json.loads(
                await self._http.get(f"/api/ProjectReference/GetAllVisibleProjectTeamMembersForContact/{user_id}")
            ),
        )

    async def get_references(self, data: dict[str, Any] | None = None) -> MetamodelGrid:
        """Get paginated project list (uses integer-keyed data pattern)."""
        response = json.loads(
            await self._http.post("/api/ProjectReference/GetProjectReferences", data=json.dumps(data or {}))
        )
        columns_raw = response.get("entityColumns", [])
        columns = [EntityColumn.model_validate(c) for c in columns_raw]
        rows = [resolve_row(columns, row) for row in response.get("data", [])]
        return MetamodelGrid(rows=rows, total_count=response.get("totalCount", len(rows)))

    async def get_filter_fields(self) -> str:
        """Get valid filter fields for use in get_references(). Returns raw JSON."""
        return await self._http.get("/api/UiView/ProjectReferencesGrid")
