# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-01-01

### Added
- Initial open source release
- `chatbotClient` — single entry point for all SDK operations
- 13-state `ConversationEngine` with full state machine
- `LocalStorage` and `S3Storage` backends
- `LLMExtractor` using GPT-4o-mini via LangChain
- `FallbackExtractor` using regex patterns (no LLM)
- `PDFFillerInterface` — pluggable PDF integration
- `PDFWorkflowManager` — polling, retry, threading
- `TelemetryCollector` with full PII anonymization
- `RateLimiter` with local and Redis backends
- `PromptBuilder` with version tracking
- Phone validation, address auto-copy utilities
- Config sample files for 10 investor types
- FastAPI reference server
- Full unit and integration test suite
