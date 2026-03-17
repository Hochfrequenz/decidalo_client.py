"""Pydantic models for the Skills domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SkillAutocomplete(BaseModel):
    skillId: int
    skillName: str
    categoryName: str | None = None
    languageID: int | None = None
    alreadyUsed: bool | None = None


class SkillLevel(BaseModel):
    skillLevelID: int
    displayName: str
    description: str | None = None
    numericalValue: int


class SkillCategory(BaseModel):
    categoryId: int
    categoryName: str
    parentCategoryId: int | None = None
    parentCategoryName: str | None = None


class SkillMapping(BaseModel):
    """Synonym/mapping entry for a skill."""
    # Response shape not fully known from HAR — use flexible model
    skillId: int | None = None
    skillName: str | None = None
    mappingDetails: Any = None
