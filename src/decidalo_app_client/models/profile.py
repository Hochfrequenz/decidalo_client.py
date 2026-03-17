"""Pydantic models for the Profile domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from decidalo_app_client.models.metamodel import ViewMetamodelEntry


class ProfileHeader(BaseModel):
    avatarImageUrl: str | None = None
    viewMetamodelResult: list[ViewMetamodelEntry] = []
    lastEditor: str | None = None
    lastEditDate: str | None = None
    approvedBy: Any = None
    approvalDate: Any = None
    canBeApproved: bool | None = None
    profileQuality: int | None = None


class ProfileCertificate(BaseModel):
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
    languageLevelID: int
    displayName: str
    numericalValue: int


class ProfileLanguage(BaseModel):
    standardLanguageID: int | None = None
    name: str
    languageLevelID: int | None = None


class ProfileLanguageSection(BaseModel):
    languages: list[ProfileLanguage]
    suggestedLanguages: list[ProfileLanguage] = []
    languageLevels: list[LanguageLevel] = []


class ProfileIndustry(BaseModel):
    industryID: int | None = None
    industryName: str
    industryCode: str | None = None
    standardIndustryID: int | None = None
    languageID: int | None = None
    projectExperienceInYears: float | None = None


class ProfileIndustrySection(BaseModel):
    industries: list[ProfileIndustry]
    suggestedIndustries: list[ProfileIndustry] = []


class ProfileRole(BaseModel):
    roleID: int
    roleSkillsCount: int = 0
    roleCertificatesCount: int = 0
    roleName: str
    roleDescription: str | None = None


class ProfileRolesSection(BaseModel):
    roles: list[ProfileRole]


class CoreCompetency(BaseModel):
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
    viewMetamodelResult: list[ViewMetamodelEntry] = []
    isSummaryTutorialCompleted: bool | None = None
