"""Pydantic models for the Teams domain."""

from __future__ import annotations

from pydantic import BaseModel


class TeamMember(BaseModel):
    teamMemberID: int
    teamMemberName: str
    teamMemberPosition: str | None = None
    avatarURL: str | None = None
    substituteID: int | None = None


class TeamDetails(BaseModel):
    teamID: int
    teamName: str
    parentTeamID: int | None = None
    teamManager: TeamMember
    additionalManagers: list[TeamMember] = []
    teamMembers: list[TeamMember] = []


class SimpleTeamMember(BaseModel):
    """Minimal team member representation (from TeamMembersUnderCurrentUser)."""
    userId: int
    displayName: str
