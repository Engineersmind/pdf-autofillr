# Operations Path Fixes - Source-Agnostic Design

## Problem
Operations were calling `get_complete_file_config()` which generated new file paths instead of using the paths already configured by entrypoints in `LocalStorageConfig`. This caused:
- Wrong output filenames like "small_4page_user1_session200_user_1_session_200_mapping.json"
- Duplicate user_id and session_id in filenames  
- Broke source-agnostic design (operations wouldn't work uniformly across AWS/Azure/GCP/local)

## Root Cause
In `handle_make_embed_file_operation` (line 954):
```python
# OLD (wrong):
file_config = config.get_complete_file_config(input_pdf_s3, user_id=user_id, session_id=session_id)
extracted_json = file_config.get('extraction', 'output_json')
```

Operations generated their own paths instead of using `config.local_extracted_json`, `config.local_mapped_json`, etc. that were already set by the entrypoint.

## Solution Applied

### 1. Updated `handle_make_embed_file_operation`
- **Line ~950**: Only call `get_complete_file_config()` for cloud storage, not for local
```python
if storage_type == 'local':
    # Local deployment: entrypoint already set all paths in config.local_*
    file_config = None
elif hasattr(config, 'output_base_path') and config.output_base_path:
    # Cloud deployment: generate structured output paths
    file_config = config.get_complete_file_config(input_pdf_s3, user_id=user_id, session_id=session_id)
```

- **Line ~970**: Use `config.local_extracted_json` for local storage
```python
if storage_type == 'local' and hasattr(config, 'local_extracted_json'):
    extracted_json = config.local_extracted_json
elif file_config:
    extracted_json = file_config["extraction_output_path"]
```

- **Line ~1010**: Skip file moving for local storage (paths already correct)
```python
if file_config and storage_type != 'local':
    # Only move files in cloud deployment
```

- **Line ~1400**: Use `config.local_headers_with_fields` for dual mapper
```python
if storage_type == 'local' and hasattr(config, 'local_headers_with_fields'):
    headers_output_path = config.local_headers_with_fields
    final_fields_output_path = config.local_final_form_fields
elif file_config and "headers" in file_config:
    # Cloud paths
```

- **Line ~1610**: Skip mapping file moving for local storage
- **Line ~1650**: Skip embedding file moving for local storage

### 2. Updated `handle_extract_operation`
- **Added `output_path` parameter** to signature (line ~76)
```python
def handle_extract_operation(
    ...
    output_path: Optional[str] = None
) -> Dict[str, Any]:
```

- **Line ~113**: Use provided output path if given
```python
if output_path:
    extraction_output_path = output_path
    logger.info(f"Using provided output path: {extraction_output_path}")
else:
    file_config = get_complete_file_config(input_file, user_id, session_id)
    extraction_output_path = file_config["extraction"]["extracted_path"]
```

### 3. Updated call to `handle_extract_operation`
- **Line ~1007**: Pass `config.local_extracted_json` for local storage
```python
extract_result = await handle_extract_operation(
    input_file=input_pdf_s3,
    user_id=user_id,
    session_id=session_id,
    notifier=notifier,
    pdf_doc_id=pdf_doc_id,
    input_json_path=input_json_s3,
    mapping_config=mapping_config,
    output_path=config.local_extracted_json if storage_type == 'local' and hasattr(config, 'local_extracted_json') else None
)
```

## Design Pattern
**Entrypoints Control Paths → Operations Use Them**

### Local Deployment:
```
1. entrypoints/local.py sets:
   config.local_extracted_json = '/tmp/processing/553_...990_extracted.json'
   config.local_mapped_json = '/tmp/processing/553_...990_mapped_fields.json'
   
2. Operations use these paths directly:
   extracted_json = config.local_extracted_json  ✅
   
3. No path generation by operations
```

### Cloud Deployment (AWS/Azure/GCP):
```
1. entrypoints/aws_lambda.py doesn't set config.local_* 
2. Operations detect no local paths
3. Operations call get_complete_file_config() to generate S3/Blob paths
4. Maintains backward compatibility
```

## Benefits
✅ **Source-Agnostic**: Operations work same way for any storage (local/AWS/Azure/GCP)  
✅ **Correct Filenames**: Uses entrypoint's naming patterns (no duplicates)  
✅ **Config-Driven**: All paths come from config.ini  
✅ **Backward Compatible**: Cloud deployments still work (fall back to file_config)

## Testing
Run local entrypoint test:
```bash
cd /Users/raghava/Documents/EMC/pdf-autofillr/modules/mapper
python -m pytest tests/test_local_entrypoint.py -v
```

Expected output files:
```
/tmp/processing/553_086d6670-81e5-47f4-aecb-e4f7c3ba2a83_990_extracted.json
/tmp/processing/553_086d6670-81e5-47f4-aecb-e4f7c3ba2a83_990_mapped_fields.json
/tmp/processing/553_086d6670-81e5-47f4-aecb-e4f7c3ba2a83_990_embedded.pdf
```

**NOT**:
```
/tmp/processing/small_4page_user1_session200_user_1_session_200_mapping.json  ❌
```

## Files Modified
- `modules/mapper/src/handlers/operations.py` (~2660 lines)
  - `handle_make_embed_file_operation()` - Multiple sections
  - `handle_extract_operation()` - Signature and path logic

## Remaining TODO
- [ ] Apply same pattern to `handle_map_operation()`  
- [ ] Apply same pattern to `handle_embed_operation()`  
- [ ] Apply same pattern to `handle_fill_operation()`  
- [ ] Test complete flow with real PDF
- [ ] Verify _save_results() correctly copies output files
