"""PDF Autofiller Python SDK."""

__version__ = "1.0.0"

from .client import MapperClient
from .exceptions import (
    APIError,
    AuthenticationError,
    MapperError,
    TimeoutError,
    ValidationError,
)

__all__ = [
    "MapperClient",
    "MapperError",
    "AuthenticationError",
    "ValidationError",
    "APIError",
    "TimeoutError",
]
