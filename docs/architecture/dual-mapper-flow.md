# Dual Mapper (RAG) File Flow Documentation

## Overview
This document explains all files created during the dual mapper (RAG) integration and their flow through the system.

## File Types Created

### 1. **Header Extraction Files**
Created by `get_form_fields_points()` from `src/headers`:

- **`headers_with_fields.json`**
  - Location: Same bucket as input PDF
  - Path pattern: `s3://bucket/path/file_headers_with_fields.json`
  - Content: Extracted PDF form fields with positions and metadata
  - Purpose: Intermediate file for header extraction

- **`final_form_fields.json`**
  - Location: Same bucket as input PDF
  - Path pattern: `s3://bucket/path/file_final_form_fields.json`
  - Content: Final processed form fields ready for RAG
  - Purpose: Input for RAG API file creation

### 2. **RAG API Input Files**
Created by `create_rag_api_files()` from `src/headers/create_rag_files.py`:

- **`header_file.json`**
  - Location: RAG bucket
  - Path pattern: `s3://rag-bucket-pdf-filler/predictions/{user_id}/{session_id}/{pdf_doc_id}/input_file/header_file.json`
  - Content: Field-level data with context for RAG API
  - Purpose: Primary input to RAG API

- **`section_file.json`**
  - Location: RAG bucket
  - Path pattern: `s3://rag-bucket-pdf-filler/predictions/{user_id}/{session_id}/{pdf_doc_id}/input_file/section_file.json`
  - Content: Hierarchical section structure
  - Purpose: Secondary input to RAG API

**IMPORTANT:** These S3 paths are sent to the RAG API. The API must have S3 access to download these files.

### 3. **Prediction Files**

- **`llm_predictions.json`** (Semantic Mapper Output)
  - Location: RAG bucket predictions folder
  - Path pattern: `s3://rag-bucket-pdf-filler/predictions/{user_id}/{session_id}/{pdf_doc_id}/predictions/llm_predictions.json`
  - Content: Semantic mapper predictions in RAG-compatible format
  - Purpose: Comparison baseline for RAG predictions

- **`rag_predictions.json`** (RAG API Output)
  - Location: RAG bucket predictions folder
  - Path pattern: `s3://rag-bucket-pdf-filler/predictions/{user_id}/{session_id}/{pdf_doc_id}/predictions/rag_predictions.json`
  - Content: RAG model predictions
  - Purpose: Machine learning predictions from RAG model
  - Created by: External RAG API (returned via API response)

- **`final_predictions.json`** (Combined Output)
  - Location: RAG bucket predictions folder
  - Path pattern: `s3://rag-bucket-pdf-filler/predictions/{user_id}/{session_id}/{pdf_doc_id}/predictions/final_predictions.json`
  - Content: Merged semantic + RAG predictions with reasoning
  - Purpose: Detailed output showing which prediction was chosen and why
  - Format: Contains full metadata, confidence scores, selection reasoning

### 4. **Mapping Files for Java Embedder**

- **`_mapping.json`** (Semantic Mapping)
  - Location: Same bucket as input PDF
  - Path pattern: `s3://bucket/path/file_mapping.json`
  - Content: `{field_id: [field_name, actual_value, confidence]}`
  - Purpose: Raw semantic mapper output

- **`_final_mapping_json_combined_java.json`** (Java-Compatible Mapping)
  - Location: Same bucket as input PDF
  - Path pattern: `s3://bucket/path/file_final_mapping_json_combined_java.json`
  - Content: `{field_id: [field_name, "", confidence]}`
  - Purpose: Java embedder input (CRITICAL: middle element MUST be empty string)
  - Created from: Either combined mapping or converted semantic mapping

## File Flow Diagram

### Dual Mapper Mode (use_second_mapper=True)

```
Input PDF
    │
    ├─→ [Semantic Mapper] ──→ _mapping.json (semantic)
    │                          │
    │                          └──→ llm_predictions.json (RAG bucket)
    │
    └─→ [Header Extractor] ──→ headers_with_fields.json
                               │
                               └──→ final_form_fields.json
                                    │
                                    └──→ [create_rag_api_files]
                                         │
                                         ├──→ header_file.json (RAG bucket)
                                         └──→ section_file.json (RAG bucket)
                                              │
                                              └──→ [RAG API Call]
                                                   │
                                                   └──→ rag_predictions.json (RAG bucket)
                                                        │
                                                        └──→ [combine_mappings]
                                                             │
                                                             ├──→ final_predictions.json (detailed)
                                                             └──→ _final_mapping_json_combined_java.json
                                                                  │
                                                                  └──→ [Java Embedder]
```

### Single Mapper Mode (use_second_mapper=False)

```
Input PDF
    │
    └─→ [Semantic Mapper] ──→ _mapping.json (semantic)
                               │
                               ├──→ llm_predictions.json (RAG bucket)
                               │
                               └──→ [convert_semantic_to_java_format]
                                    │
                                    └──→ _final_mapping_json_combined_java.json
                                         │
                                         └──→ [Java Embedder]
```

## Storage Locations

### Input PDF Bucket
Files stored alongside the input PDF:
- `headers_with_fields.json`
- `final_form_fields.json`
- `_mapping.json`
- `_final_mapping_json_combined_java.json`
- `_radio_groups.json`

### RAG Bucket (`rag-bucket-pdf-filler`)
Structure:
```
predictions/
└── {user_id}/
    └── {session_id}/
        └── {pdf_doc_id}/
            ├── input_file/
            │   ├── header_file.json
            │   └── section_file.json
            └── predictions/
                ├── llm_predictions.json
                ├── rag_predictions.json
                └── final_predictions.json
```

## RAG API Integration

### API Request
```json
{
  "api_name": "get_rag_predictions",
  "user_id": "123",
  "session_id": "session_1234567890_abcd1234",
  "pdf_id": "456",
  "header_file_location": "s3://rag-bucket-pdf-filler/predictions/123/session_1234567890_abcd1234/456/input_file/header_file.json"
}
```

**CRITICAL:** The `header_file_location` is an **S3 path**, not a local path. The RAG API must:
1. Have AWS credentials configured
2. Have read access to the RAG bucket
3. Download the file from S3 before processing

### API Response
```json
{
  "status": "success",
  "data": {
    "s3_paths": {
      "rag_predictions": "s3://rag-bucket-pdf-filler/predictions/123/session_1234567890_abcd1234/456/predictions/rag_predictions.json"
    }
  }
}
```

## Config Tracking

All these paths are tracked in `AWSStorageConfig` (`src/configs/aws.py`):

### S3 Paths (remote)
- `s3_headers_with_fields`
- `s3_final_form_fields`
- `s3_header_file`
- `s3_section_file`
- `s3_llm_predictions`
- `s3_rag_predictions`
- `s3_final_predictions`
- `s3_java_mapping`

### Local Paths (downloaded)
- `local_headers_with_fields`
- `local_final_form_fields`
- `local_header_file`
- `local_section_file`
- `local_llm_predictions`
- `local_rag_predictions`
- `local_final_predictions`
- `local_java_mapping`

## Source-Agnostic Design

While the current implementation uses S3 paths for RAG integration, the core helper functions are source-agnostic:

- `convert_semantic_to_java_format()` - Works with any storage
- `save_llm_predictions_to_rag_bucket()` - Adapts to storage type
- `combine_mappings()` - Works with any storage

**Exception:** `create_rag_api_files()` and `call_rag_api()` currently require S3 because:
1. The RAG API expects S3 paths
2. The RAG bucket is specifically an S3 bucket
3. Files must be accessible to the external RAG service

To support other cloud providers, the RAG API would need to be updated to accept different storage types.

## File Cleanup

Files are NOT automatically deleted. Consider:
- Setting S3 lifecycle policies for the RAG bucket
- Cleaning up temp files in `/tmp/` after processing
- Archiving old predictions for audit trails

## Troubleshooting

### RAG API receives S3 path but can't access file
**Solution:** Ensure RAG API has:
- AWS credentials configured
- IAM role with `s3:GetObject` permission on RAG bucket
- Network access to S3

### Files not appearing in RAG bucket
**Solution:** Check:
- `RAG_BUCKET_NAME` environment variable
- S3 upload permissions
- Bucket exists and is in the correct region

### Java embedder fails with "Not a JSON Array" error
**Solution:** Verify `_final_mapping_json_combined_java.json` format:
- Middle element MUST be empty string `""`
- NOT the actual value from input JSON
- Format: `{field_id: [field_name, "", confidence]}`
