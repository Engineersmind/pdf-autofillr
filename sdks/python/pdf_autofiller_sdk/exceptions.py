"""Custom exceptions for PDF Autofiller SDK."""


class PDFAutofillerError(Exception):
    """Base exception for all SDK errors."""
    pass


class APIError(PDFAutofillerError):
    """Raised when API returns an error response."""
    
    def __init__(self, message: str, status_code: int = None, response: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class ValidationError(PDFAutofillerError):
    """Raised when request validation fails."""
    pass


class TimeoutError(PDFAutofillerError):
    """Raised when request times out."""
    pass


class ConnectionError(PDFAutofillerError):
    """Raised when cannot connect to API."""
    pass
