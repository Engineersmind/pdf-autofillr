# Mapper Module — Test Suite

## Overview

155 tests across 10 test files. **No real data required** — no API keys, no real PDFs, no Java JARs, no network access. Every test runs fully in-process using mocks and temporary files.

---

## Running All Tests

```bash
# from modules/mapper/
./venv/bin/pytest
```

That's it. The `pyproject.toml` already configures everything:
- test discovery in `tests/`
- verbose output
- coverage report for `src/`

### Useful variations

```bash
# Run a single file
./venv/bin/pytest tests/test_llm_json.py

# Run a single test class
./venv/bin/pytest tests/test_semantic_mapper.py::TestChunkKeys

# Run a single test
./venv/bin/pytest tests/test_unified_llm_client.py::TestComplete::test_returns_llm_response

# Skip slow/external tests (none currently, but marked in pyproject.toml)
./venv/bin/pytest -m "not slow"

# Run without coverage (faster)
./venv/bin/pytest --no-cov

# Stop at first failure
./venv/bin/pytest -x
```

No shell scripts needed — pytest handles everything.

---

## Test Files

### `test_llm_json.py` — 27 tests

Tests `src/utils/llm_json.py`: the shared JSON parsing utility and Pydantic output models.

| Class | What it tests |
|---|---|
| `TestParseLlmJson` | `parse_llm_json()` — strips markdown fences, handles preamble text, raises on bad JSON |
| `TestFieldMatch` | `FieldMatch` model — coerces string `con` to float, clamps to [0,1], normalises `null`/empty keys to `None` |
| `TestMappingOutput` | `MappingOutput` RootModel — validates dict of `FieldMatch`, iteration, roundtrip from raw LLM text |

**No mocks. Pure logic.**

---

### `test_renderer.py` — 22 tests

Tests `src/prompts/renderer.py`: how `build_messages()` formats prompts for Claude vs OpenAI.

| Class | What it tests |
|---|---|
| `TestBuildMessagesClaudeSplit` | Prompt with `##CACHE_SPLIT##` → two content blocks; static block gets `cache_control` |
| `TestBuildMessagesClaudeNoSplit` | Prompt without marker → plain string content |
| `TestBuildMessagesClaudeSystem` | System message gets `cache_control`; combined with split prompt |
| `TestBuildMessagesOpenAI` | Marker stripped, plain strings only, no cache blocks |
| `TestBuildMessagesOllama` | Same as OpenAI — not Claude, no cache blocks |
| `TestClaudeModelDetection` | Parametrized: `claude-*`, `bedrock/anthropic.*`, `anthropic/*` detected as Claude; `gpt-*`, `ollama/*`, `azure/*` are not |

**No mocks. Pure logic.**

---

### `test_unified_llm_client.py` — 21 tests

Tests `src/clients/unified_llm_client.py`: the LiteLLM wrapper.

| Class | What it tests |
|---|---|
| `TestExtractUsage` | Token parsing from LiteLLM response — basic counts, Claude cache read/creation tokens, OpenAI cached tokens |
| `TestEstimateTokens` | Token counting — string messages, fallback to char/4, Claude-style list content blocks |
| `TestComplete` | `complete()` — returns `LLMResponse`, converts plain string to messages, accumulates stats, passes `max_tokens`, raises on LiteLLM error, `temperature` override |
| `TestStats` | `get_cumulative_stats()` initial zeros, `reset_stats()` clears everything |
| `TestFactoryMethods` | `create_from_settings()` reads `settings.llm_model`; `create_headers_client()` reads `settings.headers_llm_model`; Ollama sets `OLLAMA_API_BASE` env var |

**Mocks:** `litellm.completion` and `litellm.completion_cost` patched — no real API calls.

---

### `test_semantic_mapper.py` — 25 tests

Tests `src/mappers/semantic_mapper.py`: pure-logic methods and the async chunk processor.

| Class | What it tests |
|---|---|
| `TestPrepareInputData` | `prepare_updated_input_data()` returns list of keys; `prepare_updated_input_data_with_description()` extracts descriptions; `flatten_enriched_data()` strips to values |
| `TestChunkKeys` | `chunk_keys()` splits key list into N even chunks; handles edge cases (empty list, more chunks than keys) |
| `TestRemoveDuplicateKeysInTableColumns` | Deduplication of mapped keys within the same table column — keeps first row, nulls the rest; different columns with same key are both kept; non-table fields untouched |
| `TestGenerateKeyDescriptionsBulk` | Calls LLM, parses JSON result, handles fenced response, raises `JSONDecodeError` on bad JSON |
| `TestProcessChunkAsync` | Async chunk mapping — fid→(key, value, confidence) tuple; null key maps to None value; unknown key gets None value; invalid JSON returns `{}`; string `con` coerced to float |

**Mocks:** `UnifiedLLMClient.create_from_settings` patched; `mapper.llm.complete` set to return fixture responses.

---

### `test_group_by_llm.py` — 13 tests

Tests `src/groupers/group_by_llm.py`: radio/checkbox field grouping via LLM.

| Class | What it tests |
|---|---|
| `TestGetContextLines` | Collects text elements within GID window around radio fields; respects threshold; sorts by GID; returns empty when no radio fields |
| `TestGroupFieldsFromText` | Parses valid LLM JSON, handles fenced response, raises `RuntimeError` on invalid JSON, raises `ValueError` when LLM not initialized or empty response, tracks token usage |
| `TestGroupFlow` | `group()` returns `{"groups": ..., "llm_usage": ...}`; no radio fields → no LLM call; with radio fields → LLM called once, full parsed dict under `groups` key |

**Mocks:** `mock_llm` fixture — `MagicMock` with `.complete()` returning fixture `LLMResponse`.

---

### `test_extract.py` — 6 tests

Tests `handle_extract_operation` in `src/handlers/operations.py`.

| Test | What it checks |
|---|---|
| `test_success_response_shape` | Result has `status`, `operation`, `output_file`, `execution_time` keys |
| `test_pdf_hash_forwarded` | `pdf_hash` from extractor appears in the result |
| `test_output_handler_called_correctly` | `output_handler.save_output()` called with the extracted data |
| `test_missing_pdf_raises` | `FileNotFoundError` when input PDF path is `None` |
| `test_extractor_error_propagates` | Exception from `DetailedFitzExtractor.extract()` bubbles up |
| `test_storage_type_in_response` | `source_type` from config included in result |

**Mocks:** `create_file_handlers`, `DetailedFitzExtractor` patched. PDF is an empty file created with `open(path, "wb").close()`.

---

### `test_embed.py` — 8 tests

Tests `run_embed_java_stage` and `handle_embed_operation` in `src/handlers/operations.py`.

| Class | What it tests |
|---|---|
| `TestRunEmbedJavaStage` | Java JAR invocation — success returns output path; raises when JAR not found; raises when input file missing; raises on non-zero exit code; raises on timeout |
| `TestHandleEmbedOperation` | Operation wrapper — success shape; `FileNotFoundError` when input handler returns `None`; Java failure propagates |

**Mocks:** `subprocess.run`, `os.path.exists` patched. No real Java or PDF required.

---

### `test_fill.py` — 11 tests

Tests `fill_with_java`, `fill_with_java_safe`, and `handle_fill_operation` in `src/handlers/operations.py`.

| Class | What it tests |
|---|---|
| `TestFillWithJava` | Returns output path on success; raises when JAR not found; raises on Java failure; raises on timeout |
| `TestFillWithJavaSafe` | Returns `{"status": "success", ...}` dict; returns error dict (never raises) when embedded PDF missing; returns error dict on Java exception |
| `TestHandleFillOperation` | Operation wrapper — success shape and `operation == "fill"`; raises on missing embedded PDF; Java error propagates |

**Mocks:** `subprocess.run`, `os.path.exists`, `fill_with_java` patched. No real Java or PDF required.

---

### `test_headers.py` — 10 tests

Tests `src/headers/get_form_fields_points.py`.

| Class | What it tests |
|---|---|
| `TestBuildHeaderIndex` | `build_header_index()` — structural headings indexed by page; h3/h4 fields indexed by fid; empty input returns empty dicts |
| `TestFindPageHierarchy` | `find_page_hierarchy()` — returns title/h1/h2/section_context for a page; returns `None` for missing levels |
| `TestGetFormFieldsPoints` | Full async function with mocked LLM — returns success status; creates output files; fields have `hierarchy` and `fid` keys; LLM usage in result; graceful handling of invalid LLM JSON |

**Mocks:** `UnifiedLLMClient.create_headers_client` patched. Input files written to `tmp_path`.

---

### `test_integration.py` — 3 tests

Wires multiple mocked operations together to verify pipeline handoffs.

| Class | What it tests |
|---|---|
| `TestExtractMapPipeline` | Extract then Map — extract result feeds into map; both return `status == "success"` |
| `TestEmbedFillPipeline` | Embed then Fill — embedded PDF path passed correctly; both return `status == "success"` |
| `TestFullPipelineSmoke` | All four stages (Extract → Map → Embed → Fill) chained; each returns `status == "success"` |

**Mocks:** All operations fully mocked (`DetailedFitzExtractor`, `SemanticMapper`, `run_embed_java_stage`, `fill_with_java`, `create_file_handlers`). Real JSON files written to `tmp_path` to satisfy file I/O within the handlers.

---

## What Is NOT Tested Here

These are out of scope for this module's unit tests — they belong in `tests/integration/` or `tests/e2e/` at the repo root when a staging environment is available:

- Real LLM API calls (OpenAI, Bedrock, Ollama)
- Real Java JAR execution (embed/fill)
- Real PDF extraction with `DetailedFitzExtractor`
- S3 / Azure Blob / GCP storage operations
- Full Lambda entrypoint invocation
- Cross-module flows (mapper + chatbot)

---

## No Scripts Needed

Everything is driven by `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["-v", "--strict-markers", "--tb=short", "--cov=src", ...]
```

Just run `./venv/bin/pytest` from `modules/mapper/`. Coverage HTML is written to `htmlcov/index.html` after each run.
