"""
PDF Autofiller Python SDK

Client library for PDF Mapper API.
"""

__version__ = "1.0.0"

from .client import PDFMapperClient
from .resources.mapper import MapperResource

__all__ = ["PDFMapperClient", "MapperResource"]
