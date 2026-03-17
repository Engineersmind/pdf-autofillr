# rv1-fixes2 — Session Change Log

**Branch:** `rv1-fix`
**Date:** 2026-03-12
**Scope:** Cloud-agnostic storage refactor + concurrency + reliability fixes

---

## 1. Cloud-Agnostic Architecture Refactor

### Issue
Storage backend (AWS/Azure/GCP/local) was baked into config objects as flat attribute bags (~30 `s3_*`, `local_*`, `blob_*` attributes each). Adding a new file type required touching 4+ config classes. `InputFileHandler` and `OutputFileHandler` had `if/elif source_type` chains — adding a new backend meant touching both handlers, the factory, the base class, and each concrete config.

### Fix: `PathResolver` + `JobContext` + `StorageBackendFactory`

**New files:**

| File | Purpose |
|------|---------|
| `src/storage/paths/resolver.py` | `PathResolver` — single source of truth for all pipeline paths. One method per file type, backed by `FileConfig`. Adding a new pipeline file = add one method here only. |
| `src/storage/job_context.py` | `JobContext` — replaces attribute-bag config objects. Pre-populated from `PathResolver`. Maintains full backward-compat interface (`local_*`, `dest_*`, `s3_*`, `download_file`, `upload_file`) so `operations.py` needed zero changes. |
| `src/storage/backends/factory.py` | `get_storage_backend(source_type)` — lazy-cached, driven by `config.ini [general] source_type`. |
| `src/storage/__init__.py` | Package init. |
| `src/storage/paths/__init__.py` | Package init. |
| `src/storage/backends/__init__.py` | Package init. |

**Modified files:**

| File | Change |
|------|--------|
| `src/handlers/input_handler.py` | Removed all `if/elif source_type` routing. Calls `config.download_file()` directly via backend delegation. |
| `src/handlers/output_handler.py` | Same — calls `config.upload_file()` directly. Destination resolved via `dest_` → `s3_` → `blob_` → `gcs_` priority. |
| `src/utils/entrypoint_helpers.py` | Added `create_job_context(file_config, user_id, session_id, pdf_doc_id)` — single call replaces `build_all_file_paths() + prepare_input_files() + create_storage_config_from_paths()`. Old functions kept for backward compat. |
| `src/configs/aws.py` | Stripped ~35 `local_*` / `s3_*` attribute initialisations. Backend only needs `download_file`, `upload_file`, `file_exists`. Restored `global_input_json_s3_uri` env config. |
| `entrypoints/local.py` | Rewritten (~100 lines) using `create_job_context`. |

**Adding a new storage backend going forward:**
1. Create `src/configs/minio.py` implementing `download_file` / `upload_file` / `file_exists`
2. Add one entry to `_BACKEND_CLASSES` in `factory.py`
3. Set `source_type = minio` in `config.ini`

---

## 2. Concurrent Request Path Collision

### Issue
All requests shared `/tmp/processing/` as the processing directory. Filenames were parameterised by `user_id_session_id_pdf_doc_id` — different jobs were safe, but the **same job triggered twice concurrently** (double-click, client retry, HTTP server with multiple workers) wrote to identical paths, causing silent file corruption.

**Safe on Lambda** (one request per container execution). **Vulnerable on HTTP server / Docker** with multiple workers.

### Fix: UUID-scoped processing directory per `JobContext`

Each `JobContext.__init__` generates a UUID subdirectory:
```
/tmp/processing/9239e1d8-ab42-4e2b-8f74-cabae34be579/553_session-AAA_990_input.pdf
/tmp/processing/ac1dbe14-a7b2-4aa3-b202-1a1a6f69fdde/553_session-AAA_990_input.pdf
```
Two concurrent identical jobs get completely isolated temp dirs. Destination (output) paths are intentionally still shared — last writer wins, which is correct since both compute the same result.

**Files changed:**
- `src/configs/file_config.py` — added optional `processing_dir` param to `get_all_processing_paths()`
- `src/storage/paths/resolver.py` — forwarded param in `local_paths()`
- `src/storage/job_context.py` — generates UUID dir on init, exposes `ctx.processing_dir`
- `entrypoints/local.py` — cleans up `ctx.processing_dir` instead of shared base dir

---

## 3. Cleanup Not Guaranteed on Operation Failure

### Issue
Cleanup of the processing directory was called after the operation but outside a `try/finally` block. If the operation raised an exception, cleanup was skipped, leaking the UUID temp directory.

```python
# Before — cleanup skipped on failure
result = await _call_operation(...)
cleanup_processing_directory(ctx.processing_dir)  # never runs if above throws
```

### Fix: `try/finally` in all entrypoints

```python
# After — cleanup always runs
try:
    result = await _call_operation(...)
finally:
    cleanup_processing_directory(ctx.processing_dir)
```

**Files changed:** `entrypoints/local.py`, `entrypoints/http_server.py`, `entrypoints/aws_lambda.py`

---

## 4. `http_server.py` Still Using Old API

### Issue
After the `create_job_context` refactor, `http_server.py` still used the old `build_all_file_paths() + create_storage_config_from_paths()` path — no UUID isolation, no `mapping_config` passed to operations, no `try/finally` cleanup.

### Fix
Rewrote `process_operation()` to use `create_job_context`, pass `mapping_config` from `config.ini`, and wrap operation in `try/finally`.

**File changed:** `entrypoints/http_server.py`

---

## 5. `aws_lambda.py` Creating Bare `AWSStorageConfig()` with Manual Attributes

### Issue
Lambda's `make_embed_file`, `fill_pdf`, `check_embed_file`, `make_form_fields_data_points` each did:
```python
config = AWSStorageConfig()
config.s3_input_pdf = pdf_s3_url
config.local_input_pdf = f"/tmp/form_{pdf_doc_id}.pdf"  # flat /tmp/, not UUID-scoped
```
- No UUID isolation (concurrent Lambda warm-container reuse could collide)
- No `try/finally` cleanup
- Cache registry downloaded to flat `/tmp/hash_registry.json`

### Fix
Replaced with `create_job_context` for all four operations. Downloads go to UUID-scoped `ctx.local_input_pdf`. Cache registry goes to `ctx.processing_dir/hash_registry.json`. `try/finally` ensures cleanup + cache upload happen even on failure.

**File changed:** `entrypoints/aws_lambda.py`

---

## 6. Azure/GCP Backends Crash Mid-Pipeline

### Issue
`AzureStorageConfig.download_file()` and `GCPStorageConfig.download_file()` both raise `NotImplementedError`. But the error only surfaced mid-pipeline — after inputs had been downloaded and processing had started — giving a confusing crash with no guidance.

### Fix: Fail-fast at startup in `StorageBackendFactory`

```python
_IMPLEMENTED = {'aws', 'local'}

if source_type not in _IMPLEMENTED:
    raise NotImplementedError(
        f"Storage backend {source_type!r} is not yet implemented. ..."
    )
```
Setting `source_type = azure` in `config.ini` now raises immediately on first `create_job_context()` call with a clear message.

**File changed:** `src/storage/backends/factory.py`

---

## 7. No Credential Validation for Cloud Backends

### Issue
`AWSStorageConfig()` initialised successfully with no credentials. The error (boto3 `NoCredentialsError`) only appeared at the first actual S3 download — mid-pipeline, after wasted work.

### Fix: Credential check in factory before backend instantiation

```python
_CREDENTIAL_CHECKS = {
    'aws':   ['AWS_ACCESS_KEY_ID', 'AWS_ROLE_ARN'],
    'azure': ['AZURE_STORAGE_CONNECTION_STRING', 'AZURE_STORAGE_ACCOUNT'],
    'gcp':   ['GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_CLOUD_PROJECT'],
}
```
If none of the required env vars are set, raises `EnvironmentError` immediately with a list of what to set. IAM roles (`AWS_ROLE_ARN`) count as credentials for Lambda.

**File changed:** `src/storage/backends/factory.py`

---

## 8. `FileConfig` Singleton Staleness

### Issue
`get_file_config()` returns a module-level singleton. On warm Lambda containers or long-running HTTP servers, if `config.ini` changes or tests need to reload config, there was no way to reset it. The `StorageBackendFactory` also cached backend instances separately, so a reset of one didn't clear the other.

### Fix: `reset_file_config()`

```python
def reset_file_config() -> None:
    """Reset FileConfig singleton and StorageBackendFactory cache."""
    global _file_config
    _file_config = None
    from src.storage.backends.factory import clear_cache
    clear_cache()
```

Single call resets both. Primarily useful in tests and development hot-reload scenarios.

**File changed:** `src/configs/file_config.py`

---

## Summary Table

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | Attribute-bag config, if/elif handler routing | Architecture | `PathResolver` + `JobContext` + `StorageBackendFactory` |
| 2 | Same-job concurrent path collision | Critical (HTTP server) | UUID per-request processing dir in `JobContext` |
| 3 | Cleanup skipped on operation failure | High | `try/finally` in all entrypoints |
| 4 | `http_server.py` on old API | High | Rewritten to use `create_job_context` |
| 5 | Lambda using bare `AWSStorageConfig` + flat `/tmp/` | High | `create_job_context` in all Lambda operations |
| 6 | Azure/GCP crash mid-pipeline | Medium | Fail-fast `NotImplementedError` in factory |
| 7 | No credential validation | Medium | Env var check in factory before backend init |
| 8 | `FileConfig` singleton no reset path | Low | `reset_file_config()` added |
