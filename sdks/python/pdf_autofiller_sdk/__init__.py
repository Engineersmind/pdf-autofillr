"""
PDF Autofiller SDK - Python Client

A simple HTTP client for the PDF Autofiller Mapper service.
"""

from .client import PDFAutofillerClient, AsyncPDFAutofillerClient
from .exceptions import (
    PDFAutofillerError,
    APIError,
    ValidationError,
    TimeoutError as SDKTimeoutError
)

__version__ = "0.1.0"

__all__ = [
    "PDFAutofillerClient",
    "AsyncPDFAutofillerClient",
    "PDFAutofillerError",
    "APIError",
    "ValidationError",
    "SDKTimeoutError",
]
