# Changelog

## [0.1.0] - 2025-03-06

### Added
- `UploadDocumentClient` — single entry point for all SDK operations
- `ReaderFactory` with 7 format readers (PDF, DOCX, PPTX, XLSX, JSON, TXT)
- `Extractor` — LLM extraction via GPT-4.1-mini with regex fallback
- `enforce_schema` — type-safe schema enforcement ported from Lambda
- `apply_address_normalization` — address splitting ported from Lambda
- `ParallelRunner` — Thread A (extract+upload) + Thread B (embed+poll)
- `ExtractionEngine` — full 8-step pipeline orchestrator
- `PDFFillerInterface` — pluggable PDF filling abstract class
- `PDFWorkflowManager` — polling, retry, threading
- `LocalStorage` and `S3Storage` backends
- `APILogger` — full execution log saved to S3
- `document_upload_managed/` — private package folder (Auth0 + PDF Lambda)
- FastAPI local dev server
- Full unit and integration test suite
