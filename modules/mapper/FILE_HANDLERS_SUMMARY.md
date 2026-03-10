# File Handlers Implementation Summary

## Problem Solved
**User Request**: "I don't want to save after all files are created, should be done as soon file created in operations, so created OutputFile handler, (based on source save them accordingly as soon as they created)"

## Solution: Input & Output File Handlers

Created two handler classes that provide source-agnostic file I/O:

### 1. **OutputFileHandler** (`src/handlers/output_handler.py`)
- **Purpose**: Save files to source storage immediately after creation
- **Supports**: Local filesystem, AWS S3, Azure Blob, GCP Cloud Storage
- **Method**: `save_output(local_path, file_type)` - Automatically uploads/copies based on source type

### 2. **InputFileHandler** (`src/handlers/input_handler.py`)
- **Purpose**: Download/copy files from source storage before processing
- **Supports**: Local filesystem, AWS S3, Azure Blob, GCP Cloud Storage
- **Method**: `get_input(file_type)` - Automatically downloads/copies based on source type

### 3. **Unified Interface** (`src/handlers/file_handlers.py`)
- **Factory**: `create_file_handlers(config)` - Returns both handlers
- **Usage**: `input_handler, output_handler = create_file_handlers(config)`

## How It Works

### Source Type Detection
Handlers automatically detect source type from config:
- `config.source_type == 'local'` → Use copy operations
- `config.source_type == 'aws'` → Use S3 client
- `config.source_type == 'azure'` → Use Blob client
- `config.source_type == 'gcp'` → Use GCS client

### Path Resolution
Handlers map file types to config attributes:

**Local Storage:**
```python
# Processing paths (where operations work)
config.local_extracted_json = '/tmp/processing/553_990_extracted.json'

# Destination paths (where files are saved)
config.dest_extracted_json = '../../data/output/553_990_extracted.json'
```

**AWS Storage:**
```python
# Local paths (where operations work)
config.local_extracted_json = '/tmp/553_990_extracted.json'

# S3 paths (where files are uploaded)
config.s3_extracted_json = 's3://bucket/output/553_990_extracted.json'
```

### Automatic Upload/Copy
When operation creates a file:
```python
# Operation creates file
extractor.extract(pdf_path=local_pdf, storage_config={
    "type": "local",
    "path": config.local_extracted_json  # /tmp/processing/...
})

# Handler saves it immediately
output_handler.save_output(
    config.local_extracted_json,  # Source: /tmp/processing/...
    'extracted_json'               # Type: determines destination
)

# Result:
# - Local: Copied to ../../data/output/...extracted.json
# - AWS: Uploaded to s3://bucket/output/...extracted.json
```

## Implementation Details

### LocalStorageConfig Extensions
Added destination paths in entrypoint (`entrypoints/local.py`):
```python
config.dest_extracted_json = paths['source_output_extracted']
config.dest_mapped_json = paths['source_output_mapped']
config.dest_radio_json = paths['source_output_radio']
config.dest_embedded_pdf = paths['source_output_embedded']
config.dest_filled_pdf = paths['source_output_filled']
config.dest_semantic_mapping_json = paths['source_output_semantic_mapping']
config.dest_headers_with_fields_json = paths['source_output_headers']
config.dest_final_form_fields_json = paths['source_output_final_fields']
```

### Config.ini Extensions
Added output file patterns:
```ini
[file_naming]
# Output files (saved to source storage)
output_extracted_json = {user_id}_{session_id}_{pdf_doc_id}_extracted.json
output_mapped_json = {user_id}_{session_id}_{pdf_doc_id}_mapped_fields.json
output_radio_groups_json = {user_id}_{session_id}_{pdf_doc_id}_radio_groups.json
output_embedded_pdf = {user_id}_{session_id}_{pdf_doc_id}_embedded.pdf
output_filled_pdf = {user_id}_{session_id}_{pdf_doc_id}_filled.pdf

# Dual mapper outputs
output_semantic_mapping_json = {user_id}_{session_id}_{pdf_doc_id}_semantic_mapping.json
output_headers_with_fields_json = {user_id}_{session_id}_{pdf_doc_id}_headers_with_fields.json
output_final_form_fields_json = {user_id}_{session_id}_{pdf_doc_id}_final_form_fields.json
```

## Usage in Operations

### Before (Manual I/O - OLD WAY)
```python
async def handle_extract_operation(input_file: str, user_id: int, ...):
    # ❌ Manual download
    local_pdf = f"/tmp/input_{os.path.basename(input_file)}"
    download_from_source(input_file, local_pdf)
    
    # ❌ Manual path generation
    file_config = get_complete_file_config(input_file, user_id, session_id)
    extraction_output_path = file_config["extraction"]["extracted_path"]
    
    # Extract...
    result = extractor.extract(pdf_path=local_pdf, ...)
    
    # ❌ Manual upload
    upload_to_source(local_output, extraction_output_path)
    
    return {"output_file": extraction_output_path}
```

### After (With Handlers - NEW WAY)
```python
async def handle_extract_operation(config, user_id: int, ...):
    # ✅ Create handlers
    input_handler, output_handler = create_file_handlers(config)
    
    # ✅ Get input (automatic)
    local_pdf = input_handler.get_input('input_pdf')
    
    # ✅ Extract to configured path
    result = extractor.extract(
        pdf_path=local_pdf,
        storage_config={"type": "local", "path": config.local_extracted_json}
    )
    
    # ✅ Save immediately (automatic)
    output_handler.save_output(config.local_extracted_json, 'extracted_json')
    
    return {"output_file": config.local_extracted_json}
```

## Benefits

### 1. Immediate File Persistence
- **Before**: Files saved at end of entire pipeline (risk of data loss)
- **After**: Files saved immediately after creation (no data loss)

### 2. Source-Agnostic Operations
- **Before**: Different code for S3, Blob, GCS
- **After**: Same code works for all storage types

### 3. Reduced Code Complexity
- **Before**: ~20 lines of I/O code per operation
- **After**: ~5 lines of I/O code per operation

### 4. Better Error Handling
- **Before**: Manual error handling in each operation
- **After**: Centralized error handling in handlers

### 5. Easier Testing
- **Before**: Must mock S3/Blob/GCS clients in every test
- **After**: Just mock config attributes

## File Flow Examples

### Local Storage Flow
```
1. Input: ../../data/input/small_4page.pdf
2. Entrypoint copies to: /tmp/processing/553_990_input.pdf
3. Operation extracts to: /tmp/processing/553_990_extracted.json
4. OutputHandler copies to: ../../data/output/553_990_extracted.json ✅
5. Operation maps to: /tmp/processing/553_990_mapped_fields.json
6. OutputHandler copies to: ../../data/output/553_990_mapped_fields.json ✅
7. Operation embeds to: /tmp/processing/553_990_embedded.pdf
8. OutputHandler copies to: ../../data/output/553_990_embedded.pdf ✅
9. Cleanup: Delete /tmp/processing/*
10. Result: All files in ../../data/output/ ✅
```

### AWS Lambda Flow
```
1. Input: s3://bucket/input/file.pdf
2. Entrypoint downloads to: /tmp/file.pdf
3. Operation extracts to: /tmp/extracted.json
4. OutputHandler uploads to: s3://bucket/output/extracted.json ✅
5. Operation maps to: /tmp/mapped.json
6. OutputHandler uploads to: s3://bucket/output/mapped.json ✅
7. Operation embeds to: /tmp/embedded.pdf
8. OutputHandler uploads to: s3://bucket/output/embedded.pdf ✅
9. Lambda terminates: /tmp/ auto-deleted
10. Result: All files in s3://bucket/output/ ✅
```

## Files Created

1. **`src/handlers/output_handler.py`** (237 lines)
   - OutputFileHandler class
   - Handles save_output() for all storage types
   - Maps file types to destination paths

2. **`src/handlers/input_handler.py`** (267 lines)
   - InputFileHandler class
   - Handles get_input() for all storage types
   - Downloads/copies files before processing

3. **`src/handlers/file_handlers.py`** (47 lines)
   - Unified interface
   - Factory function: create_file_handlers()
   - Exports both handlers

4. **`USING_FILE_HANDLERS.md`** (Documentation)
   - Complete usage guide
   - Before/after examples
   - Migration steps

## Files Modified

1. **`entrypoints/local.py`**
   - Added `dest_*` attributes to LocalStorageConfig
   - Maps processing paths to source output paths

2. **`config.ini`**
   - Added output file naming patterns
   - Supports all pipeline stages

## Next Steps

### To Complete Implementation:

1. **Update `handle_extract_operation`**
   - Add `config` parameter
   - Remove manual download/upload code
   - Use input_handler.get_input() and output_handler.save_output()

2. **Update `handle_map_operation`**
   - Same pattern as extract

3. **Update `handle_embed_operation`**
   - Same pattern as extract

4. **Update `handle_fill_operation`**
   - Same pattern as extract

5. **Update `handle_make_embed_file_operation`**
   - Pass config to sub-operations
   - Files will be saved immediately at each stage

6. **Remove `_save_results()` from entrypoint**
   - No longer needed (files already saved by operations)
   - Keep for legacy compatibility initially

7. **Update AWS/Azure/GCP entrypoints**
   - Set s3_*/blob_*/gcs_* destination paths
   - Same pattern as local entrypoint

## Testing

Test with local storage:
```bash
cd /Users/raghava/Documents/EMC/pdf-autofillr/modules/mapper
python -m test_local_entrypoint
```

Verify files immediately available:
```bash
# Check after each stage
ls -la /tmp/processing/  # Operations working here
ls -la ../../data/modules/mapper_sample/output/  # Files saved here immediately
```

## Design Philosophy

**"Save as soon as created, not at the end"**

- ✅ Immediate persistence prevents data loss
- ✅ Operations don't need to know about storage
- ✅ Entrypoints configure paths, operations process files
- ✅ Handlers bridge the gap (config → I/O)
- ✅ Same code works for any storage type

This design follows the AWS Lambda pattern where files are saved to S3 immediately after creation, rather than waiting until the entire pipeline completes.
