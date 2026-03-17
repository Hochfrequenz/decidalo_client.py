"""Pydantic models for the Roles domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Role(BaseModel):
    roleID: int
    roleSkillsCount: int = 0
    roleCertificatesCount: int = 0
    roleName: str
    description: str | None = None
    redesignRoleID: int | None = None
    creatorID: int | None = None
    roleCode: str | None = None


class RoleSkillCheck(BaseModel):
    isFulfilled: bool
    matchedUserSkillRoles: list[Any] = []
    missingRoleSkills: list[Any] = []


class RoleCertCheck(BaseModel):
    isFulfilled: bool
    matchedUserRoleCertificates: list[Any] = []
    missingUserRoleCertificates: list[Any] = []
