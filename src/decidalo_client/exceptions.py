"""Custom exceptions for the Decidalo API client."""

from __future__ import annotations


class DecidaloClientError(Exception):
    """Base exception for all Decidalo client errors."""


class DecidaloAPIError(DecidaloClientError):
    """Exception raised when the API returns an error response.

    Attributes:
        status_code: The HTTP status code of the error response.
        message: A human-readable error message.
    """

    def __init__(self, status_code: int, message: str) -> None:
        """Initialize the API error.

        Args:
            status_code: The HTTP status code of the error response.
            message: A human-readable error message.
        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"API error {status_code}: {message}")


class DecidaloAuthenticationError(DecidaloAPIError):
    """Exception raised when authentication fails (401/403 errors)."""
