# Using File Handlers in Operations

## Overview
The `InputFileHandler` and `OutputFileHandler` provide a source-agnostic way to handle file I/O in operations. They automatically detect the storage type (local/AWS/Azure/GCP) and use the appropriate method.

## Benefits
✅ **Source-Agnostic**: Same code works for local, S3, Azure Blob, GCS  
✅ **Automatic Upload**: Files saved immediately after creation  
✅ **Simplified Operations**: No need for download_from_source/upload_to_source  
✅ **Config-Driven**: All paths come from config

## Usage Pattern

### In Operations (NEW WAY)

```python
from src.handlers.file_handlers import create_file_handlers

async def handle_extract_operation(
    input_file: str,
    user_id: int,
    session_id: int,
    config,  # Add config parameter
    ...
) -> Dict[str, Any]:
    """Extract operation with automatic file handling."""
    
    # Create handlers
    input_handler, output_handler = create_file_handlers(config)
    
    # 1. Get input file (already downloaded by entrypoint usually)
    local_pdf = input_handler.get_input('input_pdf')
    # Returns: /tmp/processing/553_990_input.pdf
    
    # 2. Run extraction
    extractor = DetailedFitzExtractor(extractor_config)
    result = extractor.extract(pdf_path=local_pdf, storage_config={
        "type": "local",
        "path": config.local_extracted_json  # Use configured path
    })
    
    # 3. Save output immediately
    output_handler.save_output(
        config.local_extracted_json,  # Local path where file was created
        'extracted_json'               # File type (for destination mapping)
    )
    # For local: Copies /tmp/processing/...extracted.json → ../../data/output/...extracted.json
    # For AWS: Uploads /tmp/...extracted.json → s3://bucket/...extracted.json
    
    return {
        "operation": "extract",
        "output_file": config.local_extracted_json,
        "pdf_hash": result.get('pdf_hash')
    }
```

### In Operations (OLD WAY - Remove This)

```python
# OLD - Don't use this anymore!
async def handle_extract_operation(input_file: str, ...):
    # ❌ Manual download
    local_pdf = f"/tmp/input_{os.path.basename(input_file)}"
    download_from_source(input_file, local_pdf)
    
    # ❌ Manual path generation
    file_config = get_complete_file_config(input_file, user_id, session_id)
    extraction_output_path = file_config["extraction"]["extracted_path"]
    
    # Extract...
    
    # ❌ Manual upload
    upload_to_source(local_output, extraction_output_path)
```

## Example: handle_extract_operation

### Before (Manual I/O)
```python
async def handle_extract_operation(
    input_file: str,
    user_id: int,
    session_id: int,
    output_path: Optional[str] = None,
    ...
):
    # Manual download
    local_pdf = f"/tmp/input_{os.path.basename(input_file)}"
    download_from_source(input_file, local_pdf)
    
    # Manual path generation
    if output_path:
        extraction_output_path = output_path
    else:
        file_config = get_complete_file_config(input_file, user_id, session_id)
        extraction_output_path = file_config["extraction"]["extracted_path"]
    
    # Extract
    result = extractor.extract(pdf_path=local_pdf, ...)
    
    # Manual upload
    upload_to_source(local_output, extraction_output_path)
    
    return {"output_file": extraction_output_path}
```

### After (With Handlers)
```python
async def handle_extract_operation(
    config,  # Add config as first parameter
    user_id: int,
    session_id: int,
    ...
):
    # Create handlers
    input_handler, output_handler = create_file_handlers(config)
    
    # Get input (automatic download if needed)
    local_pdf = input_handler.get_input('input_pdf')
    
    # Extract to configured path
    result = extractor.extract(
        pdf_path=local_pdf,
        storage_config={
            "type": "local",
            "path": config.local_extracted_json
        }
    )
    
    # Save output immediately (automatic upload)
    output_handler.save_output(
        config.local_extracted_json,
        'extracted_json'
    )
    
    return {
        "output_file": config.local_extracted_json,
        "pdf_hash": result.get('pdf_hash')
    }
```

## Example: handle_make_embed_file_operation

```python
async def handle_make_embed_file_operation(
    config,  # Storage config with all paths
    user_id: int,
    session_id: int,
    pdf_doc_id: int,
    investor_type: str,
    ...
):
    """Make embed file with automatic file handling."""
    
    # Create handlers
    input_handler, output_handler = create_file_handlers(config)
    
    # Stage 1: Extract
    extract_result = await handle_extract_operation(
        config=config,
        user_id=user_id,
        session_id=session_id,
        ...
    )
    # File automatically saved to source storage ✅
    
    # Stage 2: Map
    map_result = await handle_map_operation(
        config=config,
        extracted_json_path=config.local_extracted_json,
        ...
    )
    # File automatically saved to source storage ✅
    
    # Stage 3: Embed
    embed_result = await handle_embed_operation(
        config=config,
        mapping_json_path=config.local_mapped_json,
        ...
    )
    # File automatically saved to source storage ✅
    
    return {
        "operation": "make_embed_file",
        "outputs": {
            "extracted_json": config.local_extracted_json,
            "mapped_json": config.local_mapped_json,
            "embedded_pdf": config.local_embedded_pdf
        }
    }
```

## Config Structure

### LocalStorageConfig (Entrypoint Sets These)
```python
config = LocalStorageConfig()

# Processing paths (where operations work)
config.local_input_pdf = '/tmp/processing/553_990_input.pdf'
config.local_extracted_json = '/tmp/processing/553_990_extracted.json'
config.local_mapped_json = '/tmp/processing/553_990_mapped_fields.json'
config.local_embedded_pdf = '/tmp/processing/553_990_embedded.pdf'

# Destination paths (where OutputFileHandler saves)
config.dest_extracted_json = '../../data/output/553_990_extracted.json'
config.dest_mapped_json = '../../data/output/553_990_mapped_fields.json'
config.dest_embedded_pdf = '../../data/output/553_990_embedded.pdf'
```

### AWSStorageConfig
```python
config = AWSStorageConfig()

# Local paths (where operations work in /tmp/)
config.local_input_pdf = '/tmp/553_990_input.pdf'
config.local_extracted_json = '/tmp/553_990_extracted.json'

# S3 paths (where OutputFileHandler uploads)
config.s3_input_pdf = 's3://bucket/input/553_990.pdf'
config.s3_extracted_json = 's3://bucket/output/553_990_extracted.json'
```

## Migration Steps

### 1. Update Operation Signatures
Add `config` as first parameter:
```python
# Before
async def handle_extract_operation(input_file: str, user_id: int, ...):

# After
async def handle_extract_operation(config, user_id: int, ...):
```

### 2. Remove Manual I/O Code
Delete these lines:
```python
# ❌ Remove these
from src.core.config import get_complete_file_config
from src.clients.s3_client import download_from_source, upload_to_source

local_pdf = f"/tmp/input_{os.path.basename(input_file)}"
download_from_source(input_file, local_pdf)

file_config = get_complete_file_config(input_file, user_id, session_id)
extraction_output_path = file_config["extraction"]["extracted_path"]

upload_to_source(local_output, extraction_output_path)
```

### 3. Add Handler Code
```python
# ✅ Add these
from src.handlers.file_handlers import create_file_handlers

input_handler, output_handler = create_file_handlers(config)

# Get input
local_pdf = input_handler.get_input('input_pdf')

# Save output
output_handler.save_output(config.local_extracted_json, 'extracted_json')
```

### 4. Update Operation Calls
When calling operations, pass config:
```python
# Before
extract_result = await handle_extract_operation(
    input_file=input_pdf_s3,
    user_id=user_id,
    ...
)

# After
extract_result = await handle_extract_operation(
    config=config,
    user_id=user_id,
    ...
)
```

## File Flow

### Local Storage
```
1. Entrypoint copies: ../../data/input/file.pdf → /tmp/processing/file.pdf
2. Operation processes: /tmp/processing/file.pdf → /tmp/processing/extracted.json
3. OutputHandler copies: /tmp/processing/extracted.json → ../../data/output/extracted.json
4. Cleanup deletes: /tmp/processing/*
```

### AWS Lambda
```
1. Entrypoint downloads: s3://bucket/input/file.pdf → /tmp/file.pdf
2. Operation processes: /tmp/file.pdf → /tmp/extracted.json
3. OutputHandler uploads: /tmp/extracted.json → s3://bucket/output/extracted.json
4. Lambda terminates (auto-cleanup)
```

## Benefits Summary

| Aspect | Before (Manual) | After (Handlers) |
|--------|----------------|------------------|
| **Code Lines** | ~20 lines per operation | ~5 lines per operation |
| **Source-Agnostic** | ❌ Different code for each storage | ✅ Same code for all storage |
| **File Upload Timing** | ❌ At end (can lose data) | ✅ Immediately after creation |
| **Path Management** | ❌ Manual path generation | ✅ Config-driven paths |
| **Error Handling** | ❌ Must implement per operation | ✅ Built into handlers |
| **Testability** | ❌ Hard to test (needs mocking) | ✅ Easy to test (mock config) |
