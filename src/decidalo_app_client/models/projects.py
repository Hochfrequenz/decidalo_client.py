"""Pydantic models for the Projects domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from decidalo_app_client.models.metamodel import ViewMetamodelEntry


class ProjectHeader(BaseModel):
    viewMetamodelResult: list[ViewMetamodelEntry] = []


class ProjectProfileEntry(BaseModel):
    id: int | None = None
    avatarImageUrl: str | None = None
    name: str | None = None
    position: str | None = None
    isAnonymized: bool | None = None


class ProjectOverview(BaseModel):
    profileEntries: list[ProjectProfileEntry] = []
    planningStartDate: str | None = None
    planningEndDate: str | None = None
    bookedMembers: list[Any] = []
    resourceManager: Any = None
    projectManager: Any = None
    substituteProjectManager: Any = None
    salesResponsible: Any = None
    viewMetamodelResult: list[ViewMetamodelEntry] = []


class ProjectDetails(BaseModel):
    viewMetamodelResult: list[ViewMetamodelEntry] = []


class ProjectTeamMember(BaseModel):
    """Team member on a project. Shape confirmed from HAR only as empty list — model is best-effort."""
    userId: int | None = None
    displayName: str | None = None
    jobPosition: str | None = None
    avatarImageUrl: str | None = None
