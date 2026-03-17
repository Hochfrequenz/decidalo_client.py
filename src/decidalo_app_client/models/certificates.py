"""Pydantic models for the Certificates domain."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CertificateAutocomplete(BaseModel):
    certificateID: int
    certificateName: str


class CertificateHolder(BaseModel):
    userID: int
    displayName: str
    expirationMonth: int | None = None
    expirationYear: int | None = None
    avatarImageUrl: str | None = None


class CertificateHoldersResponse(BaseModel):
    certificateHolders: list[CertificateHolder]
    totalCount: int
