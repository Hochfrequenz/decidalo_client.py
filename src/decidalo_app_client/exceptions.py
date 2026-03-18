"""Custom exceptions for the Decidalo App API client."""

from __future__ import annotations


class AppAPIError(Exception):
    """Raised when the App API returns an error response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"App API error {status_code}: {message}")


class AppAuthError(Exception):
    """Raised when authentication fails or cannot be refreshed."""
