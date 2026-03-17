"""Pydantic models for the Projects domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from decidalo_app_client.models.metamodel import ViewMetamodelEntry


class ProjectHeader(BaseModel):
    """Header metadata for a project."""

    viewMetamodelResult: list[ViewMetamodelEntry] = []


class ProjectProfileEntry(BaseModel):
    """A profile entry (person) associated with a project."""

    id: int | None = None
    avatarImageUrl: str | None = None
    name: str | None = None
    position: str | None = None
    isAnonymized: bool | None = None


class ProjectOverview(BaseModel):
    """Overview data for a project including team and planning dates."""

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
    """Detailed metadata fields for a project."""

    viewMetamodelResult: list[ViewMetamodelEntry] = []


class ProjectTeamMember(BaseModel):
    """Team member on a project. Shape confirmed from HAR only as empty list — model is best-effort."""

    userId: int | None = None
    displayName: str | None = None
    jobPosition: str | None = None
    avatarImageUrl: str | None = None
