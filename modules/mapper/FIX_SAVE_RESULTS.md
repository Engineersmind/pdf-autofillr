# Fix: Copy Results from Processing to Source Storage

## Problem Identified
Operations were saving files to `/tmp/processing/` (Docker ephemeral storage) but files were NOT being copied back to source storage (`../../data/output/`).

The user correctly pointed out:
> "you are not copying them to source from docker local, what? once file is created, should be uploaded to source based on source type"

## Root Cause
The `_save_results()` function in `entrypoints/local.py` was:
1. Only checking for `'embedded_pdf_path'` in result (wrong key)
2. Only saving embedded and filled PDFs (missing intermediate files)
3. Not handling the actual result structure from operations

Operations return:
```python
{
    "operation": "make_embed_file",
    "outputs": {
        "extracted_json": "/tmp/processing/..._extracted.json",
        "mapping_json": "/tmp/processing/..._mapped_fields.json",
        "radio_groups_json": "/tmp/processing/..._radio_groups.json",
        "embedded_pdf": "/tmp/processing/..._embedded.pdf",
        "semantic_mapping_json": "/tmp/processing/..._semantic_mapping.json",
        "headers_with_fields": "/tmp/processing/..._headers_with_fields.json",
        "final_form_fields": "/tmp/processing/..._final_form_fields.json"
    }
}
```

## Solution Applied

### 1. Updated `_save_results()` in `entrypoints/local.py`
Now copies ALL output files from operations:

```python
def _save_results(...):
    # Handle make_embed_file operation output
    if 'outputs' in result:
        outputs = result['outputs']
        
        # Copy extracted JSON
        if 'extracted_json' in outputs:
            shutil.copy2(src, dst)
        
        # Copy mapping JSON
        if 'mapping_json' in outputs:
            shutil.copy2(src, dst)
        
        # Copy radio groups JSON
        if 'radio_groups_json' in outputs:
            shutil.copy2(src, dst)
        
        # Copy embedded PDF (main output)
        if 'embedded_pdf' in outputs:
            shutil.copy2(src, dst)
        
        # Copy dual mapper outputs (if used)
        if 'semantic_mapping_json' in outputs:
            shutil.copy2(src, dst)
        
        if 'headers_with_fields' in outputs:
            shutil.copy2(src, dst)
        
        if 'final_form_fields' in outputs:
            shutil.copy2(src, dst)
```

### 2. Updated `_build_file_paths()` in `entrypoints/local.py`
Added destination paths for all output files:

```python
# Source output paths (where results go)
paths['source_output_extracted'] = file_config.get_source_output_path(
    'extracted_json', user_id, session_id, pdf_doc_id
)
paths['source_output_mapped'] = file_config.get_source_output_path(
    'mapped_json', user_id, session_id, pdf_doc_id
)
paths['source_output_radio'] = file_config.get_source_output_path(
    'radio_groups_json', user_id, session_id, pdf_doc_id
)
paths['source_output_embedded'] = file_config.get_source_output_path(
    'embedded_pdf', user_id, session_id, pdf_doc_id
)
# ... etc for dual mapper outputs
```

### 3. Updated `config.ini`
Added output file naming patterns:

```ini
[file_naming]
# Output files (in source storage - /app/data/output for local)
output_extracted_json = {user_id}_{session_id}_{pdf_doc_id}_extracted.json
output_mapped_json = {user_id}_{session_id}_{pdf_doc_id}_mapped_fields.json
output_radio_groups_json = {user_id}_{session_id}_{pdf_doc_id}_radio_groups.json
output_embedded_pdf = {user_id}_{session_id}_{pdf_doc_id}_embedded.pdf
output_filled_pdf = {user_id}_{session_id}_{pdf_doc_id}_filled.pdf

# Dual mapper output files
output_semantic_mapping_json = {user_id}_{session_id}_{pdf_doc_id}_semantic_mapping.json
output_headers_with_fields_json = {user_id}_{session_id}_{pdf_doc_id}_headers_with_fields.json
output_final_form_fields_json = {user_id}_{session_id}_{pdf_doc_id}_final_form_fields.json
```

## Complete File Flow

### Before (WRONG):
```
1. Input: ../../data/input/small_4page.pdf
2. Copy to: /tmp/processing/553_...990_input.pdf
3. Operations create: /tmp/processing/553_...990_extracted.json
4. Operations create: /tmp/processing/553_...990_mapped_fields.json
5. Operations create: /tmp/processing/553_...990_embedded.pdf
6. ❌ Files stay in /tmp/processing/
7. Cleanup deletes all files from /tmp/processing/
8. ❌ NO OUTPUT FILES!
```

### After (CORRECT):
```
1. Input: ../../data/input/small_4page.pdf
2. Copy to: /tmp/processing/553_...990_input.pdf
3. Operations create: /tmp/processing/553_...990_extracted.json
4. Operations create: /tmp/processing/553_...990_mapped_fields.json  
5. Operations create: /tmp/processing/553_...990_embedded.pdf
6. ✅ _save_results() copies ALL files:
   - /tmp/processing/...extracted.json → ../../data/output/...extracted.json
   - /tmp/processing/...mapped_fields.json → ../../data/output/...mapped_fields.json
   - /tmp/processing/...radio_groups.json → ../../data/output/...radio_groups.json
   - /tmp/processing/...embedded.pdf → ../../data/output/...embedded.pdf
7. Cleanup deletes /tmp/processing/* (safe now!)
8. ✅ ALL OUTPUT FILES IN ../../data/output/
```

## Source-Agnostic Design

This pattern works for ANY storage:

### Local Deployment:
```
Source → Docker ephemeral → Source
../../data/input/ → /tmp/processing/ → ../../data/output/
```

### AWS Lambda:
```
Source → Lambda /tmp/ → Source  
s3://bucket/input/ → /tmp/ → s3://bucket/output/
```

### Azure Functions:
```
Source → Function /tmp/ → Source
azure://container/input/ → /tmp/ → azure://container/output/
```

## Files Modified
- `modules/mapper/entrypoints/local.py` - `_save_results()` and `_build_file_paths()`
- `modules/mapper/config.ini` - Added output file patterns

## Testing
Run local entrypoint:
```bash
cd /Users/raghava/Documents/EMC/pdf-autofillr/modules/mapper
python -m test_local_entrypoint
```

Verify output files exist:
```bash
ls -la ../../data/modules/mapper_sample/output/
```

Expected files:
- `553_086d6670-81e5-47f4-aecb-e4f7c3ba2a83_990_extracted.json`
- `553_086d6670-81e5-47f4-aecb-e4f7c3ba2a83_990_mapped_fields.json`
- `553_086d6670-81e5-47f4-aecb-e4f7c3ba2a83_990_radio_groups.json`
- `553_086d6670-81e5-47f4-aecb-e4f7c3ba2a83_990_embedded.pdf`

## Benefits
✅ **Complete File Preservation**: All operation outputs saved to source storage  
✅ **Source-Agnostic**: Pattern works for local/AWS/Azure/GCP  
✅ **Ephemeral Storage Pattern**: Matches AWS Lambda behavior  
✅ **No Data Loss**: Files copied before cleanup  
✅ **Config-Driven**: All paths from config.ini
