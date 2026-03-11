# Path Configuration Fix Summary

## Problem
Helper functions in `operations.py` were hardcoding `/tmp/` for temporary file processing, which:
- Doesn't respect config.ini's `processing_dir` setting
- Won't work if `/tmp/` doesn't exist or isn't writable
- Breaks the design pattern of getting all paths from config

## Solution
All temp file operations now use the **directory of the file being processed**, which is set by:
1. **config.ini** defines `processing_dir = /tmp/processing`
2. **Entrypoint** (local.py) reads config.ini and sets `config.processing_dir`
3. **Operations** download files to processing_dir and work there
4. **Helper functions** use the same directory as their input files

## Files Fixed

### 1. `entrypoints/local.py`
**Added**: `config.processing_dir = paths['processing_dir']` 
- Config object now carries the processing directory from config.ini

### 2. `src/handlers/operations.py`

**Fixed Functions:**

#### `convert_semantic_to_java_format()` (Lines ~2328-2420)
- **Before**: `semantic_temp = f"/tmp/semantic_to_java_{user_id}_{pdf_doc_id}.json"`
- **After**: Uses `work_dir = os.path.dirname(semantic_mapping_path)`
- **Benefit**: Temp files created in same directory as input file

#### `save_llm_predictions_to_rag_bucket()` (Lines ~2437-2495)
- **Before**: `semantic_temp = f"/tmp/semantic_mapping_{user_id}_{pdf_doc_id}.json"`
- **After**: Uses `work_dir = os.path.dirname(semantic_mapping_path)`
- **Benefit**: Temp files respect processing directory from config

#### `combine_mappings()` (Lines ~2503-2750)
- **Before**: 
  - `semantic_temp = f"/tmp/semantic_mapping_{user_id}_{pdf_doc_id}.json"`
  - `rag_temp = f"/tmp/rag_predictions_{user_id}_{pdf_doc_id}.json"`
  - `final_temp = f"/tmp/final_predictions_{user_id}_{pdf_doc_id}.json"`
  - `java_mapping_temp = f"/tmp/java_mapping_{user_id}_{pdf_doc_id}.json"`
- **After**: All use `work_dir = os.path.dirname(semantic_mapping_path)`
- **Benefit**: All temporary processing in configured processing directory

#### `handle_make_form_fields_data_points()` (Lines ~1855-1920)
- **Before**: 
  - `local_extracted = f"/tmp/{os.path.basename(extracted_json_path)}"`
  - `local_analysis = f"/tmp/{os.path.basename(analysis_output_path)}"`
- **After**: Uses `work_dir = os.path.dirname(extracted_json_path)`
- **Benefit**: Analysis files created in processing directory

## How It Works

### Example Flow:

1. **config.ini** says: `processing_dir = /tmp/processing`

2. **Entrypoint** reads config:
   ```python
   paths['processing_dir'] = file_config.get('local', 'processing_dir')
   config.processing_dir = paths['processing_dir']
   ```

3. **Files get downloaded to processing_dir**:
   ```
   /tmp/processing/553_086d6670_990_extracted.json
   /tmp/processing/553_086d6670_990_semantic_mapping.json
   ```

4. **Helper functions use same directory**:
   ```python
   # Input: /tmp/processing/553_086d6670_990_semantic_mapping.json
   work_dir = os.path.dirname(semantic_mapping_path)  # → /tmp/processing
   semantic_temp = os.path.join(work_dir, f"semantic_to_java_{user_id}_{pdf_doc_id}.json")
   # → /tmp/processing/semantic_to_java_553_990.json
   ```

5. **All temp files stay in processing_dir** ✅

## Benefits

✅ **Config-driven**: All paths from config.ini
✅ **Consistent**: Everything in same processing directory
✅ **Flexible**: Works with any processing_dir setting
✅ **Clean**: Temp files stay together, easy to cleanup
✅ **Docker-safe**: Works in container environments
✅ **Cloud-ready**: Works with S3/Azure paths (falls back to tempfile.gettempdir())

## Testing

Test with different config.ini settings:
```ini
# Local development
processing_dir = /tmp/processing

# Docker container
processing_dir = /app/tmp

# Custom location
processing_dir = /var/app/processing
```

All should work! 🎉
