# Mapper Refactor Guide

## Overview

The mapper system has been refactored into two clean, testable phases with individual cache checks:

### Phase 1: Semantic Mapper (`run_semantic_api_mapper`)
- **Input**: extracted JSON + input/global JSON template
- **Output**: `semantic_mapping.json` (raw LLM output with metadata wrapper)
- **Cache**: Stores `semantic_mapping.json` as source of truth
- **Format**: `{"user_id": "...", "predictions": {...}}` OR unwrapped `{"field_2": {...}}`

### Phase 2: RAG Mapper (`run_rag_api_mapper`)
- **Input**: extracted JSON + headers file (final_form_fields.json)
- **Output**: `rag_predictions.json` (RAG API output with top_k matches)
- **Cache**: Stores `rag_predictions.json` separately
- **Format**: See `data/samples/sample_rag.json`

## File Formats

### 1. Semantic Mapping (semantic_mapping.json)
**Purpose**: Raw LLM output from semantic mapper (Phase 1)  
**Storage**: **CACHED** - This is the source of truth  
**Format Examples**:

#### Wrapped Format (with metadata):
```json
{
  "user_id": "553",
  "session_id": "...",
  "predictions": {
    "field_2": {
      "predicted_field_name": "investor_full_legal_name_id",
      "confidence": 0.95
    },
    "field_3": {
      "predicted_field_name": "investor_ssn_id",
      "confidence": 0.95
    }
  }
}
```

#### Unwrapped Format (predictions only):
```json
{
  "field_2": {
    "predicted_field_name": "investor_full_legal_name_id",
    "confidence": 0.95
  },
  "field_3": {
    "predicted_field_name": "investor_ssn_id",
    "confidence": 0.95
  }
}
```

### 2. RAG Predictions (rag_predictions.json)
**Purpose**: Enhanced predictions from RAG API (Phase 2)  
**Storage**: **CACHED** - Stored separately from semantic mapping  
**Format**:
```json
{
  "user_id": "553",
  "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
  "pdf_id": "990",
  "model": "rag",
  "timestamp": "2026-02-19T22:16:47.681728Z",
  "pdf_hash": "aeff9d3d...",
  "predictions": {
    "field_8": {
      "predicted_field_name": "investormailingaddressline1_ID",
      "confidence": 0.8589439221898064,
      "vector_id": "vec_023",
      "top_k": [
        {
          "field_name": "investormailingaddressline1_ID",
          "confidence": 0.8589439221898064,
          "vector_id": "vec_023"
        },
        {
          "field_name": "investormailingaddressline2_ID",
          "confidence": 0.8130911446298085,
          "vector_id": "vec_024"
        }
      ],
      "similarity_margin": 0.04585277755999795
    }
  }
}
```

### 3. Java Mapping (mapped_fields.json)
**Purpose**: Java-compatible format for PDF embedder  
**Storage**: **NOT CACHED** - Derived on-demand from semantic_mapping.json  
**Format**:
```json
{
  "1": [null, null, 0],
  "2": ["investor_full_legal_name_id", "", 0.95],
  "3": ["investor_ssn_id", "", 0.95],
  "4": ["commitment_amount_id", "", 0.85]
}
```

**CRITICAL**: The middle element in the array MUST be an empty string `""`, not the actual value!  
- ✅ Correct: `["field_name", "", 0.95]`
- ❌ Wrong: `["field_name", "553", 0.95]` → Java fails with "Not a JSON Array: '553'"

## Refactored Functions

### `run_semantic_api_mapper()`

Located in: `modules/mapper/src/handlers/operations.py` (lines ~933-1115)

**Purpose**: Run semantic mapper (Phase 1) with cache support

**Parameters**:
```python
extracted_json_path: str      # Path to extracted JSON from extract stage
input_json_path: str          # Path to input/global JSON template
storage_config: Any           # Storage configuration object
user_id: int                  # User ID
pdf_doc_id: int               # PDF document ID
session_id: Optional[int]     # Optional session ID
pdf_hash: Optional[str]       # PDF content hash for cache lookup
cache_registry_path: str      # Path to cache registry file
investor_type: str            # Investor type for mapping (default: 'individual')
mapping_config: Optional[dict] # Optional mapping configuration
notifier: Optional[Any]       # Optional notification system
```

**Returns**:
```python
{
    "semantic_mapping_path": str,  # Path to semantic_mapping.json (local/processing)
    "radio_groups_path": str,      # Path to radio_groups.json (local/processing)
    "dest_semantic_mapping": str,  # Destination path in persistent storage (for cache)
    "dest_radio_groups": str,      # Destination path in persistent storage (for cache)
    "cache_hit": bool              # True if loaded from cache, False if ran mapper
}
```

**Cache Logic**:
1. Check cache first using `pdf_hash`
2. If **HIT**: Download cached `semantic_mapping.json` + `radio_groups.json` → return paths
3. If **MISS**: Run semantic mapper → save outputs → register in cache → return paths

**Usage Example**:
```python
semantic_result = await run_semantic_api_mapper(
    extracted_json_path=extracted_json,
    input_json_path=input_json,
    storage_config=config,
    user_id=user_id,
    pdf_doc_id=pdf_doc_id,
    session_id=session_id,
    pdf_hash=pdf_hash,
    cache_registry_path=cache_registry_path
)

semantic_mapping_path = semantic_result["semantic_mapping_path"]
cache_hit = semantic_result["cache_hit"]
```

---

### `run_rag_api_mapper()`

Located in: `modules/mapper/src/handlers/operations.py` (lines ~1121-1290)

**Purpose**: Run RAG mapper (Phase 2) with cache support

**Parameters**:
```python
extracted_json_path: str      # Path to extracted JSON
headers_file_path: str        # Path to final_form_fields.json (required by RAG API)
storage_config: Any           # Storage configuration object
user_id: int                  # User ID
pdf_doc_id: int               # PDF document ID
session_id: Optional[int]     # Optional session ID
pdf_hash: Optional[str]       # PDF content hash for cache lookup
cache_registry_path: str      # Path to cache registry file
notifier: Optional[Any]       # Optional notification system
```

**Returns**:
```python
{
    "rag_predictions_path": str,   # Path to rag_predictions.json (local/processing)
    "dest_rag_predictions": str,   # Destination path in persistent storage (for cache)
    "cache_hit": bool,             # True if loaded from cache, False if called API
    "success": bool,               # True if RAG API succeeded, False if failed
    "error": Optional[str]         # Error message if failed, None if succeeded
}
```

**Cache Logic**:
1. Check cache first using `pdf_hash` + "rag_predictions" key
2. If **HIT**: Download cached `rag_predictions.json` → return path
3. If **MISS**: Call RAG API → save output → register in cache → return path

**Usage Example**:
```python
rag_result = await run_rag_api_mapper(
    extracted_json_path=extracted_json,
    headers_file_path=headers_file,  # From headers extraction
    storage_config=config,
    user_id=user_id,
    pdf_doc_id=pdf_doc_id,
    session_id=session_id,
    pdf_hash=pdf_hash,
    cache_registry_path=cache_registry_path
)

if rag_result["success"]:
    rag_predictions_path = rag_result["rag_predictions_path"]
else:
    logger.warning(f"RAG API failed: {rag_result['error']}")
    # Fall back to semantic mapping only
```

---

## Complete Pipeline Flow

### Recommended Usage Pattern:

```python
async def handle_make_embed_file_operation(...):
    """Complete pipeline: Extract → Map (Phase 1 + 2) → Embed"""
    
    # Stage 1: Extract
    extract_result = await handle_extract_operation(...)
    extracted_json = extract_result["output_file"]
    pdf_hash = extract_result.get("pdf_hash")
    
    # Stage 2: Semantic Mapper (Phase 1) with cache
    semantic_result = await run_semantic_api_mapper(
        extracted_json_path=extracted_json,
        input_json_path=input_json,
        storage_config=config,
        user_id=user_id,
        pdf_doc_id=pdf_doc_id,
        session_id=session_id,
        pdf_hash=pdf_hash,
        cache_registry_path=cache_registry_path
    )
    
    semantic_mapping_path = semantic_result["semantic_mapping_path"]
    radio_groups_path = semantic_result["radio_groups_path"]
    
    # Stage 3: RAG Mapper (Phase 2) with cache - OPTIONAL
    if use_second_mapper:
        # Extract headers first (required by RAG API)
        headers_result = await extract_headers(extracted_json, ...)
        headers_file_path = headers_result["final_form_fields_path"]
        
        rag_result = await run_rag_api_mapper(
            extracted_json_path=extracted_json,
            headers_file_path=headers_file_path,
            storage_config=config,
            user_id=user_id,
            pdf_doc_id=pdf_doc_id,
            session_id=session_id,
            pdf_hash=pdf_hash,
            cache_registry_path=cache_registry_path
        )
        
        if rag_result["success"]:
            # Merge RAG predictions with semantic mapping
            merged_mapping = await merge_predictions(
                semantic_mapping_path,
                rag_result["rag_predictions_path"]
            )
            semantic_mapping_path = merged_mapping
    
    # Stage 4: Convert semantic to Java format for embedder
    mapped_fields_path = await convert_semantic_to_java_format(
        semantic_mapping_path=semantic_mapping_path,
        user_id=user_id,
        pdf_doc_id=pdf_doc_id
    )
    
    # Stage 5: Embed
    config.local_mapped_json = mapped_fields_path  # Use Java format
    embed_result = await handle_embed_operation(
        config=config,
        ...
    )
    
    # Stage 6: Cache registration (if not already cached)
    if not semantic_result["cache_hit"]:
        await save_hash_cache(
            pdf_hash=pdf_hash,
            cache_registry_path=cache_registry_path,
            mapping_json=semantic_result["dest_semantic_mapping"],  # Cache raw semantic
            radio_groups=semantic_result["dest_radio_groups"],
            embedded_pdf=embed_result["dest_output_file"],
            rag_predictions=rag_result.get("dest_rag_predictions") if use_second_mapper else None,
            user_id=user_id,
            pdf_doc_id=pdf_doc_id
        )
```

## Key Principles

1. **Cache stores raw formats**: 
   - `semantic_mapping.json` (with wrapper) is cached
   - `rag_predictions.json` is cached separately
   - `mapped_fields.json` (Java format) is NOT cached - derived on-demand

2. **Separation of concerns**:
   - Each mapper has its own function
   - Each mapper has its own cache check
   - Clear input/output contracts

3. **Error handling**:
   - RAG mapper can fail gracefully - fall back to semantic only
   - Cache errors don't break the pipeline - just re-run mapper

4. **Format conversion**:
   - Use `convert_semantic_to_java_format()` to create `mapped_fields.json`
   - This strips wrapper and converts to Java array format
   - Always use empty string `""` in middle position of array

## File Naming Conventions

From `config.ini`:
- **Line 290**: `mapped_json = {user_id}_{session_id}_{pdf_doc_id}_mapped_fields.json` (Java format)
- **Line 313**: `output_semantic_mapping_json = {user_id}_{session_id}_{pdf_doc_id}_semantic_mapping.json` (raw format)

## Sample Files

Located in: `/Users/raghava/Documents/EMC/pdf-autofillr/data/samples/`

- **z_first_phase_mapping.json** - Semantic mapper output (already in Java array format)
- **sample_rag.json** - RAG API output (with metadata wrapper and top_k predictions)
- **example_java_mapping_combined.json** - Final Java format for embedder

## Testing

To test the refactored functions:

```python
# Test semantic mapper with cache
semantic_result_1 = await run_semantic_api_mapper(...)
assert semantic_result_1["cache_hit"] == False  # First run

semantic_result_2 = await run_semantic_api_mapper(...)
assert semantic_result_2["cache_hit"] == True   # Second run (cache hit)

# Test RAG mapper with cache
rag_result_1 = await run_rag_api_mapper(...)
assert rag_result_1["cache_hit"] == False
assert rag_result_1["success"] == True

rag_result_2 = await run_rag_api_mapper(...)
assert rag_result_2["cache_hit"] == True  # Cache hit

# Test format conversion
java_path = await convert_semantic_to_java_format(semantic_mapping_path, ...)
with open(java_path, 'r') as f:
    java_data = json.load(f)

# Verify Java format
for field_id, mapping in java_data.items():
    assert isinstance(mapping, list)
    assert len(mapping) == 3
    assert mapping[1] == ""  # Middle element must be empty string
```

## Migration Notes

If migrating from old code:

1. Replace cache check logic in `handle_make_embed_file_operation` with calls to `run_semantic_api_mapper()`
2. Replace RAG API call logic with calls to `run_rag_api_mapper()`
3. Ensure cache registration uses `dest_semantic_mapping` (not `dest_mapped_json`)
4. Keep `convert_semantic_to_java_format()` call before embed stage
5. Update config paths: `config.local_mapped_json = mapped_fields_path` (Java format for embedder)

## Troubleshooting

### Java embedder fails with "Not a JSON Array: '553'"
**Cause**: Passing semantic format (with actual values) to Java embedder instead of Java format (with empty strings)  
**Fix**: Use `convert_semantic_to_java_format()` before embedding

### Cache hit but files not found
**Cause**: Cache registry references files that were deleted or moved  
**Fix**: Clear cache and re-run, or implement cache validation

### RAG mapper always fails
**Cause**: Missing `headers_file_path` or RAG API configuration  
**Fix**: Check `settings.rag_api_url` is configured, ensure headers extraction runs before RAG mapper

### Semantic mapping has wrapper but code expects unwrapped
**Cause**: Different LLM outputs or model versions  
**Fix**: Code handles both formats - checks for "predictions" key and strips if present

## Future Improvements

1. **Parallel execution**: Run semantic and RAG mappers in parallel (they're independent after headers extraction)
2. **Cache versioning**: Add version field to cache to handle format changes
3. **Smarter merging**: Improve prediction merging logic to handle conflicts
4. **Validation**: Add schema validation for all file formats
5. **Metrics**: Track cache hit rates, mapper success rates, conversion times

## References

- **Main operations file**: `modules/mapper/src/handlers/operations.py`
- **Sample files**: `data/samples/*.json`
- **Cache utilities**: `src/utils/hash_cache.py`
- **Config**: `modules/mapper/config.ini` (lines 290, 313)
