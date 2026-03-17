"""Pydantic models for the Profile domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from decidalo_app_client.models.metamodel import ViewMetamodelEntry


class ProfileHeader(BaseModel):
    """Header metadata for a user profile."""

    avatarImageUrl: str | None = None
    viewMetamodelResult: list[ViewMetamodelEntry] = []
    lastEditor: str | None = None
    lastEditDate: str | None = None
    approvedBy: Any = None
    approvalDate: Any = None
    canBeApproved: bool | None = None
    profileQuality: int | None = None


class ProfileCertificate(BaseModel):
    """A certificate entry on a user's profile."""

    userCertificateID: int
    certificateID: int
    certificateName: str
    standardCertificateID: int | None = None
    issueMonth: int | None = None
    issueYear: int | None = None
    issuerOrganizationName: str | None = None
    expirationMonth: int | None = None
    expirationYear: int | None = None
    credentialUrl: str | None = None


class LanguageLevel(BaseModel):
    """Proficiency level definition for a language."""

    languageLevelID: int
    displayName: str
    numericalValue: int


class ProfileLanguage(BaseModel):
    """A language entry on a user's profile."""

    standardLanguageID: int | None = None
    name: str
    languageLevelID: int | None = None


class ProfileLanguageSection(BaseModel):
    """Section of a profile containing language entries."""

    languages: list[ProfileLanguage]
    suggestedLanguages: list[ProfileLanguage] = []
    languageLevels: list[LanguageLevel] = []


class ProfileIndustry(BaseModel):
    """An industry entry on a user's profile."""

    industryID: int | None = None
    industryName: str
    industryCode: str | None = None
    standardIndustryID: int | None = None
    languageID: int | None = None
    projectExperienceInYears: float | None = None


class ProfileIndustrySection(BaseModel):
    """Section of a profile containing industry entries."""

    industries: list[ProfileIndustry]
    suggestedIndustries: list[ProfileIndustry] = []


class ProfileRole(BaseModel):
    """A role entry on a user's profile."""

    roleID: int
    roleSkillsCount: int = 0
    roleCertificatesCount: int = 0
    roleName: str
    roleDescription: str | None = None


class ProfileRolesSection(BaseModel):
    """Section of a profile containing role entries."""

    roles: list[ProfileRole]


class CoreCompetency(BaseModel):
    """A core competency entry on a user's profile."""

    coreCompetencyID: str
    displayText: str


class ProfileSkillPreview(BaseModel):
    """PROVISIONAL: skillId and skillName are missing from HAR sample (truncated).
    Verify actual response shape against a live API call."""

    skillId: int | None = None
    skillName: str | None = None
    lastUsed: str | None = None
    accumulatedExperienceInYears: float | None = None
    skillProjectNumber: int | None = None
    skillCategory: str | None = None
    isTranslatable: bool | None = None
    description: str | None = None
    isCoreSkill: bool | None = None
    isTopSkill: bool | None = None
    editor: str | None = None
    editDate: str | None = None


class ProfileEmployeeInfoSection(BaseModel):
    """Section of a profile containing employee info fields."""

    viewMetamodelResult: list[ViewMetamodelEntry] = []
    isSummaryTutorialCompleted: bool | None = None
