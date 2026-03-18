"""Pydantic models for the Certificates domain."""

from __future__ import annotations

from pydantic import BaseModel


class CertificateAutocomplete(BaseModel):
    """Autocomplete entry for a certificate."""

    certificateID: int
    certificateName: str


class CertificateHolder(BaseModel):
    """A user who holds a certificate."""

    userID: int
    displayName: str
    expirationMonth: int | None = None
    expirationYear: int | None = None
    avatarImageUrl: str | None = None


class CertificateHoldersResponse(BaseModel):
    """Paginated response containing certificate holders."""

    certificateHolders: list[CertificateHolder]
    totalCount: int
