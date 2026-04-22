# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.1] — 2026-03-10

### Fixed
- Added `CorrectionResult` dataclass to `correctors/base.py` — was referenced in examples but missing from the codebase
- Added `find_by_name(field_name)` method to `VectorStoreBackend` base and all 5 implementations (Local, S3, Pinecone, Chroma, Weaviate)
- `FeedbackPipeline._find_vector_by_name()` now uses `vector_store.find_by_name()` instead of hardcoded `vectors/vector_database.json` path — fixes silent failures with Pinecone/Chroma/Weaviate on CASE_B/CASE_C feedback
- Fixed `ChromaStore` constructor call in `examples/plugin_examples.py`: `collection_name=` → `collection=`
- Fixed custom corrector example: uses correct method name `generate_corrected_field_name` and returns `dict` instead of undefined `CorrectionResult`
- Exported `NoOpEmbeddingBackend` from top-level `ragpdf.__init__` and `__all__`
- Updated `managed/__init__.py` from empty stub to descriptive placeholder

### Added
- `tests/unit/test_find_by_name.py` — unit tests for `find_by_name()` across vector stores

## [0.1.0] — 2026-03-10

### Added
- `RAGPDFClient` — single public entry point with 6 typed methods
- Pluggable storage backends: `LocalStorage`, `S3Storage`
- Pluggable embedding backends: `SentenceTransformerBackend`, `OpenAIEmbeddingBackend`
- Pluggable vector store backends: `LocalVectorStore`, `S3VectorStore`, `PineconeStore`, `ChromaStore`, `WeaviateStore`
- Pluggable LLM corrector backends: `OpenAICorrectorBackend`, `AnthropicCorrectorBackend`, `NoOpCorrectorBackend`
- Full 5-case classification engine (CASE_A through CASE_E)
- Confidence decay/growth with embedding regeneration on errors
- 5-level time series: pdf_hash / category / subcategory / doctype / global
- Metrics: accuracy, coverage, confidence, agreement, recovery, case distribution
- Analytics API: pdf, category, subcategory, doctype, global, compare, pdf_hash, system_info
- Error analytics with date/category/type filters
- FastAPI dev server
- Full unit test suite (7 test files, no API keys required)
- Integration test suite with dummy embedding backend
- GitHub Actions CI/CD
