"""Exceptions raised by the PDF Autofiller SDK."""


class MapperError(Exception):
    """Base exception for all SDK errors."""


class AuthenticationError(MapperError):
    """Invalid or missing API key."""


class ValidationError(MapperError):
    """Request payload is missing or has invalid parameters."""


class APIError(MapperError):
    """The Lambda returned a non-2xx status or an error body."""

    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class TimeoutError(MapperError):
    """Request to the Lambda Function URL timed out."""
