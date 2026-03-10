"""Upload Document SDK — Document extraction and PDF filling pipeline."""
from uploaddocument.client import UploadDocumentClient
from uploaddocument.storage.local_storage import LocalStorage
from uploaddocument.storage.s3_storage import S3Storage
from uploaddocument.config.schema_config import SchemaConfig
from uploaddocument.pdf.interface import PDFFillerInterface
from uploaddocument.telemetry.config import TelemetryConfig
from uploaddocument.telemetry.document_context import DocumentContext
from uploaddocument.telemetry.collector import TelemetryCollector

__version__ = "0.1.0"
__all__ = [
    "UploadDocumentClient",
    "LocalStorage",
    "S3Storage",
    "SchemaConfig",
    "PDFFillerInterface",
    "TelemetryConfig",
    "DocumentContext",
    "TelemetryCollector",
]