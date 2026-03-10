# Local Deployment Architecture - Design Complete ✅

## Overview

This design implements a **source-agnostic architecture** where all storage sources (AWS, Azure, GCP, Local) follow the same pattern:

```
Event → Entrypoint (source-specific) → Operations (source-agnostic) → Cleanup → Result
```

---

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. EVENT (Same format for ALL sources)                         │
│    {                                                             │
│      "operation": "make_embed_file",                            │
│      "user_id": 553,                                            │
│      "session_id": "086d...",                                   │
│      "pdf_doc_id": 990                                          │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. ENTRYPOINT (Source-specific)                                 │
│                                                                  │
│  entrypoints/local.py:                                          │
│    - Reads config.ini                                           │
│    - Builds file paths from patterns                            │
│    - Copies: /app/data/input/ → /tmp/processing/               │
│                                                                  │
│  entrypoints/aws_lambda.py:                                     │
│    - Reads config.ini                                           │
│    - Builds file paths from patterns                            │
│    - Downloads: s3://bucket/ → /tmp/processing/                │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. OPERATIONS (SOURCE-AGNOSTIC!)                                │
│                                                                  │
│  handlers/operations.py:                                        │
│    Works ONLY with /tmp/processing/ paths                      │
│    - extract()  → /tmp/processing/xxx_extracted.json           │
│    - map()      → /tmp/processing/xxx_mapped.json              │
│    - embed()    → /tmp/processing/xxx_embedded.pdf             │
│    - fill()     → /tmp/processing/xxx_filled.pdf               │
│                                                                  │
│  Same code for ALL sources! ✅                                  │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. SAVE RESULTS (Source-specific)                               │
│                                                                  │
│  Local:  /tmp/processing/ → /app/data/output/                  │
│  AWS:    /tmp/processing/ → s3://bucket/output/                │
│  Azure:  /tmp/processing/ → azure://container/output/          │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. CLEANUP (All sources)                                        │
│    Delete all /tmp/processing/* files                           │
│    (Like Lambda ephemeral storage)                              │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. RESULT                                                        │
│    {                                                             │
│      "status": "success",                                       │
│      "output_paths": {                                          │
│        "filled_pdf": "/app/data/output/553_xxx_990_filled.pdf" │
│      }                                                           │
│    }                                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Design Principles

### 1. **Same Event Format**
All sources receive identical events:
```json
{
  "operation": "make_embed_file",
  "user_id": 553,
  "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
  "pdf_doc_id": 990,
  "investor_type": "individual",
  "use_second_mapper": true
}
```

### 2. **File Path Patterns (config.ini)**
All file paths are built from patterns in config.ini:

```ini
[file_naming]
input_pdf_pattern = {user_id}_{session_id}_{pdf_doc_id}.pdf
filled_pdf = {user_id}_{session_id}_{pdf_doc_id}_filled.pdf
```

### 3. **Three Storage Layers**

#### Layer 1: Source Storage (Different per source)
```
Local:  /app/data/input/553_xxx_990.pdf
AWS:    s3://bucket/input/553_xxx_990.pdf
Azure:  azure://container/input/553_xxx_990.pdf
```

#### Layer 2: Docker Processing (SAME for all!)
```
All:    /tmp/processing/553_xxx_990_input.pdf
        /tmp/processing/553_xxx_990_filled.pdf
```

#### Layer 3: Source Output (Different per source)
```
Local:  /app/data/output/553_xxx_990_filled.pdf
AWS:    s3://bucket/output/553_xxx_990_filled.pdf
Azure:  azure://container/output/553_xxx_990_filled.pdf
```

### 4. **Operations are Source-Agnostic**
```python
# handlers/operations.py - SAME for ALL sources!

def handle_make_embed_file_operation(config, user_id, ...):
    # Works with local paths only
    extract(config.local_input_pdf)      # /tmp/processing/xxx.pdf
    map(config.local_extracted_json)     # /tmp/processing/xxx.json
    embed(config.local_mapped_json)      # /tmp/processing/xxx.pdf
    
    # Doesn't care about S3, Blob, or GCS!
```

### 5. **Ephemeral Storage (Like Lambda)**
All temp files deleted after processing:
```python
# After operation completes
cleanup("/tmp/processing/*")  # Delete all temp files
```

---

## File Structure

```
modules/mapper/
  config.ini                    # ← Path patterns & storage config
  .env                          # ← API keys, secrets
  
  entrypoints/
    local.py                    # ← NEW: Local entrypoint
    aws_lambda_handler.py       # ← AWS entrypoint (TODO)
    azure_function.py           # ← Azure entrypoint (TODO)
  
  src/
    configs/
      file_config.py            # ← NEW: Config.ini loader
      base.py                   # Base storage config
      local.py                  # Local storage config
      aws.py                    # AWS storage config
    
    handlers/
      operations.py             # ← Orchestrator (source-agnostic)
```

---

## Implementation Details

### config.ini Structure

```ini
[general]
source_type = local

[local]
input_base_path = /app/data/input
output_base_path = /app/data/output
processing_dir = /tmp/processing
local_global_json = /app/data/pdf_registry.json

[aws]
bucket_name = my-bucket
input_prefix = input/
output_prefix = output/

[file_naming]
# Variables: {user_id}, {session_id}, {pdf_doc_id}
input_pdf_pattern = {user_id}_{session_id}_{pdf_doc_id}.pdf
filled_pdf = {user_id}_{session_id}_{pdf_doc_id}_filled.pdf
```

### Local Entrypoint Flow

```python
# entrypoints/local.py

def handle_local_event(event):
    # 1. Load config
    config = get_file_config()
    
    # 2. Build paths
    source_pdf = "/app/data/input/553_xxx_990.pdf"
    processing_pdf = "/tmp/processing/553_xxx_990_input.pdf"
    
    # 3. Copy in
    copy(source_pdf, processing_pdf)
    
    # 4. Process (source-agnostic!)
    result = operations.handle_operation(processing_pdf, ...)
    
    # 5. Copy out
    copy("/tmp/processing/xxx_filled.pdf", "/app/data/output/xxx_filled.pdf")
    
    # 6. Cleanup
    cleanup("/tmp/processing/*")
    
    # 7. Return
    return {"output_paths": {"/app/data/output/xxx_filled.pdf"}}
```

---

## How SDK Interacts

### Option A: Volume Mounts (Same Machine)

```python
# Docker started with volume mount
# docker run -v ~/data:/app/data mapper

# SDK puts files in mounted directory
shutil.copy("my.pdf", "/app/data/input/553_xxx_990.pdf")

# SDK calls API
result = sdk.make_embed_file(user_id=553, ...)

# SDK reads from mounted directory
output = open("/app/data/output/553_xxx_990_filled.pdf")
```

### Option B: Upload/Download API (Different Machines)

```python
# SDK uploads files
pdf_id = sdk.upload("/local/my.pdf", 
                    destination="/app/data/input/553_xxx_990.pdf")

# SDK calls API
result = sdk.make_embed_file(user_id=553, ...)

# SDK downloads result
sdk.download(result['output_paths']['filled_pdf'], 
            "/local/output.pdf")
```

---

## Comparison: Local vs AWS

### Local
```python
# Source: /app/data/input/553_xxx_990.pdf
copy_file(source, processing)           # Copy in
process(processing_file)                # Process
copy_file(processing, output)           # Copy out
cleanup(processing)                     # Cleanup
# Result: /app/data/output/553_xxx_990_filled.pdf
```

### AWS Lambda
```python
# Source: s3://bucket/input/553_xxx_990.pdf
s3_download(source, processing)         # Download
process(processing_file)                # Process (SAME!)
s3_upload(processing, output)           # Upload
cleanup(processing)                     # Cleanup (SAME!)
# Result: s3://bucket/output/553_xxx_990_filled.pdf
```

**Only difference: Download/upload mechanism!**

---

## Benefits

1. ✅ **Consistent across all sources** - Same event format, same operations
2. ✅ **Source-agnostic operations** - Core logic doesn't care about storage
3. ✅ **Config-driven** - All paths from config.ini, easy to change
4. ✅ **Ephemeral like Lambda** - Clean up temp files automatically
5. ✅ **Easy testing** - Can test locally before deploying to cloud
6. ✅ **Maintainable** - Change storage without touching operations

---

## Next Steps

1. ✅ Design complete
2. ✅ Config.ini created with patterns
3. ✅ file_config.py created (path builder)
4. ✅ entrypoints/local.py created (local handler)
5. ⏳ Update api_server.py to call entrypoint
6. ⏳ Test with real PDF
7. ⏳ Create AWS entrypoint (aws_lambda_handler.py)
8. ⏳ Create Azure entrypoint (azure_function.py)
9. ⏳ Update SDK to handle upload/download

---

## Testing

```bash
# Test local entrypoint
python test_local_entrypoint.py

# Should show:
# ✅ Files copied from source → processing
# ✅ Operations executed
# ✅ Results copied to output
# ✅ Temp files cleaned up
```

---

## Questions Answered ✅

1. **How to handle files in local Docker?** 
   → Copy from /app/data/input/ to /tmp/processing/, process, copy to /app/data/output/

2. **Same pattern for all sources?** 
   → Yes! Only download/upload differs, operations are identical

3. **Where are paths defined?** 
   → config.ini with patterns using {user_id}, {session_id}, {pdf_doc_id}

4. **Cleanup like Lambda?** 
   → Yes! Delete all /tmp/processing/* after each invocation

5. **How does SDK work?** 
   → Either volume mounts (same machine) or upload/download API (different machines)

---

**Design Status: COMPLETE ✅**

Ready to implement and test!
