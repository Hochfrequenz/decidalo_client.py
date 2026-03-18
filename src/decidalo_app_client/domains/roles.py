"""Roles domain client."""

from __future__ import annotations

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.models.roles import Role, RoleCertCheck, RoleSkillCheck


class RolesDomain:
    """Methods for querying role definitions and checking user fit."""

    def __init__(self, http: HttpHelper) -> None:
        self._http = http

    async def get(self, role_id: int) -> Role:
        """Get role definition."""
        response_text = await self._http.get(f"/api/Role/{role_id}")
        return Role.model_validate_json(response_text)

    async def check_user_skills(self, role_id: int, user_id: int) -> RoleSkillCheck:
        """Check whether a user fulfills the skill requirements for a role."""
        response_text = await self._http.get(f"/api/Role/{role_id}/User/{user_id}/Skills")
        return RoleSkillCheck.model_validate_json(response_text)

    async def check_user_certificates(self, role_id: int, user_id: int) -> RoleCertCheck:
        """Check whether a user fulfills the certificate requirements for a role."""
        response_text = await self._http.get(f"/api/Role/{role_id}/User/{user_id}/Certificates")
        return RoleCertCheck.model_validate_json(response_text)
