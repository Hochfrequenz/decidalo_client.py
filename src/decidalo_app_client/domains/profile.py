"""Profile domain client."""

from __future__ import annotations

import json

from pydantic import TypeAdapter

from decidalo_app_client._http import HttpHelper
from decidalo_app_client.models.metamodel import EntityColumn, MetamodelGrid, resolve_row
from decidalo_app_client.models.profile import (
    CoreCompetency,
    LanguageLevel,
    ProfileCertificate,
    ProfileEmployeeInfoSection,
    ProfileHeader,
    ProfileIndustrySection,
    ProfileLanguageSection,
    ProfileRolesSection,
    ProfileSkillPreview,
)


class ProfileDomain:
    """Methods for reading user profiles."""

    def __init__(self, http: HttpHelper) -> None:
        self._http = http

    async def get_header(self, user_id: int) -> ProfileHeader:
        """Get profile header (avatar, quality score, last editor, viewMetamodelResult)."""
        response_text = await self._http.get(f"/api/Profile/{user_id}/Header")
        return ProfileHeader.model_validate_json(response_text)

    async def get_skills_preview(self, user_id: int) -> list[ProfileSkillPreview]:
        """Get top/core skills preview. NOTE: skillId/skillName may be missing — model is provisional."""
        response_text = await self._http.get(f"/api/Profile/{user_id}/SkillsPreview")
        adapter = TypeAdapter(list[ProfileSkillPreview])
        return adapter.validate_json(response_text)

    async def get_roles(self, user_id: int) -> ProfileRolesSection:
        """Get roles assigned to the user."""
        response_text = await self._http.get(f"/api/Profile/{user_id}/RolesSection")
        return ProfileRolesSection.model_validate_json(response_text)

    async def get_projects(self, user_id: int) -> MetamodelGrid:
        """Get project history (uses integer-keyed data pattern — rows resolved by column name)."""
        response = json.loads(await self._http.get(f"/api/Profile/{user_id}/ProjectsSection"))
        columns_raw = response.get("entityColumns", [])
        columns = [EntityColumn.model_validate(c) for c in columns_raw]
        rows = [resolve_row(columns, row) for row in response.get("data", [])]
        return MetamodelGrid(rows=rows, total_count=response.get("totalCount", len(rows)))

    async def get_professional_experience(self, user_id: int) -> MetamodelGrid:
        """Get professional experience (uses integer-keyed data pattern)."""
        response = json.loads(await self._http.get(f"/api/Profile/{user_id}/ProfessionalExperienceSection"))
        columns_raw = response.get("entityColumns", [])
        columns = [EntityColumn.model_validate(c) for c in columns_raw]
        rows = [resolve_row(columns, row) for row in response.get("data", [])]
        return MetamodelGrid(rows=rows, total_count=response.get("totalCount", len(rows)))

    async def get_certificates(self, user_id: int) -> list[ProfileCertificate]:
        """Get certificates held by the user."""
        response_text = await self._http.get(f"/api/Profile/{user_id}/Certificates")
        adapter = TypeAdapter(list[ProfileCertificate])
        return adapter.validate_json(response_text)

    async def get_languages(self, user_id: int) -> ProfileLanguageSection:
        """Get languages and proficiency levels."""
        response_text = await self._http.get(f"/api/Profile/{user_id}/LanguageSection")
        return ProfileLanguageSection.model_validate_json(response_text)

    async def get_industries(self, user_id: int) -> ProfileIndustrySection:
        """Get industries with years of experience."""
        response_text = await self._http.get(f"/api/Profile/{user_id}/IndustrySection")
        return ProfileIndustrySection.model_validate_json(response_text)

    async def get_employee_info(self, user_id: int) -> ProfileEmployeeInfoSection:
        """Get employee metadata (uses viewMetamodelResult pattern)."""
        response_text = await self._http.get(f"/api/Profile/{user_id}/EmployeeInfoSection")
        return ProfileEmployeeInfoSection.model_validate_json(response_text)

    async def get_core_competencies(self, user_id: int) -> list[CoreCompetency]:
        """Get soft skills / core competencies."""
        response_text = await self._http.get(f"/api/Profile/{user_id}/CoreCompetencies")
        adapter = TypeAdapter(list[CoreCompetency])
        return adapter.validate_json(response_text)

    async def get_language_levels(self) -> list[LanguageLevel]:
        """Get language level reference data."""
        response_text = await self._http.get("/api/Profile/LanguageLevels")
        adapter = TypeAdapter(list[LanguageLevel])
        return adapter.validate_json(response_text)
