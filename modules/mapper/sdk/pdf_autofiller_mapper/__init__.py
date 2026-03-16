"""
PDF Autofiller Python SDK

Embedded SDK and HTTP API client for AI-powered PDF form filling.
"""

__version__ = "1.0.0"

from .client import PDFMapperClient
from .resources.mapper import MapperResource
from .mapper import PDFMapper
from .result import SDKResult, StageResult
from .exceptions import (
    PDFMapperError,
    ConfigurationError,
    ExtractionError,
    MappingError,
    EmbeddingError,
    FillingError,
    APIError,
    ConnectionError,
    TimeoutError,
)

__all__ = [
    # Clients
    "PDFMapperClient",
    "MapperResource",
    # Embedded SDK
    "PDFMapper",
    # Results
    "SDKResult",
    "StageResult",
    # Exceptions
    "PDFMapperError",
    "ConfigurationError",
    "ExtractionError",
    "MappingError",
    "EmbeddingError",
    "FillingError",
    "APIError",
    "ConnectionError",
    "TimeoutError",
]
