"""Pydantic models for the Search domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SearchKeyword(BaseModel):
    keyword: str


class MetamodelFilter(BaseModel):
    viewMetamodelEntryID: int
    filterValues: list[str] = []
    rangeStart: str | None = None
    rangeEnd: str | None = None


class GlobalSearchRequest(BaseModel):
    keywords: list[SearchKeyword]
    startDate: str | None = None
    endDate: str | None = None
    metamodelFilters: list[MetamodelFilter] = []
    useTextSearch: bool = False
    resourceRequestID: int | None = None


class SearchUser(BaseModel):
    userId: int
    userData: Any = None
    highlights: Any = None
    score: float | None = None
    matchedSkills: Any = None
    matchedCertificates: Any = None
    languages: Any = None
    industries: Any = None
    statusInResourceRequest: Any = None


class KeywordWithSynonyms(BaseModel):
    keyword: str
    skillWithSynonyms: Any = None
    certificateWithSynonyms: Any = None
    languages: Any = None
    industries: Any = None


class GlobalSearchResponse(BaseModel):
    usersWithMatchedQualities: list[SearchUser]
    keywordsWithSynonyms: list[KeywordWithSynonyms]
    globalSearchSessionID: int


class UserForAutocomplete(BaseModel):
    userID: int
    displayName: str
    jobPosition: str | None = None
    lastVisited: str | None = None
    imageUrl: str | None = None
    creatorID: int | None = None
    isAlreadyAdded: bool | None = None
