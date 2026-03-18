"""Teams domain client."""

from __future__ import annotations

from pydantic import TypeAdapter

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.models.teams import SimpleTeamMember, TeamDetails

_TEAM_MEMBERS_ADAPTER = TypeAdapter(list[SimpleTeamMember])


class TeamsDomain:
    """Methods for querying teams and their members."""

    def __init__(self, http: HttpHelper) -> None:
        self._http = http

    async def get_details(self, team_id: int) -> TeamDetails:
        """Get team details including manager and members."""
        response_text = await self._http.get(f"/api/Teams/{team_id}/TeamDetails")
        return TeamDetails.model_validate_json(response_text)

    async def get_by_manager(self, manager_id: int) -> str:
        """Get teams managed by a user. Returns raw JSON (shape unconfirmed from HAR)."""
        return await self._http.get(f"/api/Teams/GetTeamsByManager/{manager_id}")

    async def get_members_under_current_user(self) -> list[SimpleTeamMember]:
        """Get all team members visible to the currently authenticated user."""
        response_text = await self._http.get("/api/Teams/TeamMembersUnderCurrentUser")
        return _TEAM_MEMBERS_ADAPTER.validate_json(response_text)

    async def get_resource_group_members(self) -> str:
        """Get resource group members by manager. Returns raw JSON (shape unconfirmed from HAR)."""
        return await self._http.get("/api/ResourceGroup/GetResourceGroupsMembersByManager")
