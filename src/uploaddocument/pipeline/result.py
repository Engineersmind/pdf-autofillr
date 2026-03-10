"""ExtractionResult — dataclass returned by UploadDocumentClient.process_document()."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractionResult:
    """
    Result of a complete document extraction and (optionally) PDF fill.

    Attributes:
        user_id:            User identifier.
        session_id:         Session identifier.
        document_format:    File extension of the source document e.g. ".pdf".
        extracted_data:     Nested dict matching form_keys.json schema exactly.
        extracted_flat:     Flat dot-notation dict of all extracted fields.
        method:             "llm" or "fallback".
        pdf_result:         Whatever fill_document() returned (URL, S3 key, etc.) or None.
        fields_extracted:   Count of non-empty fields in extracted_flat.
        fields_in_schema:   Total fields defined in form_keys.json.
        completion_pct:     fields_extracted / fields_in_schema as a percentage.
        extraction_latency: Seconds the LLM extraction took.
        total_duration:     Seconds the full process_document() call took.
        errors:             List of error messages encountered during processing.
        s3_result_uri:      S3 URI of extraction_result.json (if S3 storage used).
        s3_flat_uri:        S3 URI of extraction_result_flat.json (if S3 storage used).
        s3_logs_uri:        S3 URI of execution_logs.json (if log_s3_uri was passed).
    """
    user_id: str
    session_id: str
    document_format: str = ""
    extracted_data: dict = field(default_factory=dict)
    extracted_flat: dict = field(default_factory=dict)
    method: str = "llm"
    pdf_result: Optional[object] = None
    fields_extracted: int = 0
    fields_in_schema: int = 0
    completion_pct: float = 0.0
    extraction_latency: float = 0.0
    total_duration: float = 0.0
    errors: list = field(default_factory=list)
    s3_result_uri: Optional[str] = None
    s3_flat_uri: Optional[str] = None
    s3_logs_uri: Optional[str] = None

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> dict:
        """Return a lightweight summary dict — useful for API responses."""
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "success": self.success,
            "method": self.method,
            "document_format": self.document_format,
            "fields_extracted": self.fields_extracted,
            "fields_in_schema": self.fields_in_schema,
            "completion_pct": self.completion_pct,
            "extraction_latency_ms": int(self.extraction_latency * 1000),
            "total_duration_ms": int(self.total_duration * 1000),
            "pdf_filled": self.pdf_result is not None,
            "errors": self.errors,
        }