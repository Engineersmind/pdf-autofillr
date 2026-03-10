# PDF Autofiller - Final Architecture Summary

**Date**: March 2, 2026

---

## The Truth About Stage 2 (Dual Mapper)

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: Dual Mapper (make_embed_file operation)                │
└─────────────────────────────────────────────────────────────────┘

STEP 1: PARALLEL (asyncio.gather) - ~8-10s
├─→ Semantic Mapper (LLM-based, runs in mapper_lambda)
│   └─→ Output: semantic_mapping.json
│
└─→ Headers Extractor (LLM-based, runs in mapper_lambda)
    └─→ Output: headers_with_fields.json
    └─→ Output: final_form_fields.json

STEP 2: SEQUENTIAL (after parallel complete) - ~2-3s
└─→ Call RAG Lambda API: get_rag_predictions
    ├─→ Input: final_form_fields.json (from headers extractor)
    ├─→ Process: Vector DB search
    └─→ Output: rag_predictions.json

STEP 3: ENSEMBLE - ~0.5s
├─→ Input: semantic_mapping.json + rag_predictions.json
├─→ Process: Compare confidences, best of both
└─→ Output: final_mapping.json (Java format)
            combined_predictions.json (detailed)
```

---

## What Runs in Parallel?

**PARALLEL (asyncio.gather)**:
1. Semantic mapper (Claude/GPT LLM calls)
2. Headers extractor (Claude/GPT LLM calls for header classification)

Both run **locally** in mapper_lambda, both make LLM API calls.

**NOT PARALLEL** (sequential after parallel):
3. RAG Lambda API call (uses headers output as input)

---

## Why This Architecture?

1. **Semantic mapper** and **Headers extractor** can run in parallel because they don't depend on each other - both just need the extracted PDF fields

2. **RAG API call** must wait for headers extractor to finish because it needs the `final_form_fields.json` as input

3. This gives partial parallelization:
   - Total time = max(semantic_time, headers_time) + rag_time + ensemble_time
   - Example: max(5s, 8s) + 2s + 0.5s = 10.5s
   - Without parallelization: 5s + 8s + 2s + 0.5s = 15.5s
   - **Savings: ~5 seconds (32% faster)**

---

## Complete make_embed_file Flow

```
mapper_lambda.make_embed_file(user_id, pdf_doc_id, session_id, ...)
│
├─→ Stage 1: EXTRACT (2-3s)
│   └─→ PyMuPDF extracts PDF structure
│   └─→ Output: form_extracted.json
│
├─→ Stage 2: DUAL MAP (10-11s total)
│   │
│   ├─→ PARALLEL (8-10s) - asyncio.gather
│   │   ├─→ Semantic Mapper (local LLM)
│   │   │   └─→ semantic_mapping.json
│   │   │
│   │   └─→ Headers Extractor (local LLM)
│   │       └─→ headers_with_fields.json
│   │       └─→ final_form_fields.json
│   │
│   ├─→ SEQUENTIAL (2-3s)
│   │   └─→ call_rag_api(final_form_fields.json)
│   │       └─→ POST to rag_lambda.get_rag_predictions
│   │       └─→ rag_predictions.json
│   │
│   └─→ ENSEMBLE (0.5s)
│       └─→ combine_mappings(semantic_mapping, rag_predictions)
│       └─→ final_mapping.json
│       └─→ combined_predictions.json
│
└─→ Stage 3: EMBED (1-2s)
    └─→ Java iText embeds field metadata
    └─→ Output: form_embedded.pdf
```

---

## Mapper Lambda Operations

**3 operations** (called by pdf_upload_lambda):

### 1. make_embed_file
- Does: Extract → Dual Map (parallel + sequential) → Embed
- Returns: form_embedded.pdf

### 2. check_embed_file
- Does: Poll S3 to check if embed ready
- Returns: Status + path

### 3. fill_pdf
- Does: Java iText fills form with data
- Returns: form_filled.pdf

---

## RAG Lambda Operations

**2 operations**:

### 1. get_rag_predictions (Sync)
- **Called by**: mapper_lambda during Stage 2 (after headers extracted)
- **Input**: final_form_fields.json (headers file)
- **Process**: Generate embeddings, search vector DB
- **Returns**: rag_predictions.json

### 2. set_operation / saving_filled_pdf (Async)
- **Called by**: Background process after PDF delivered to user
- **Input**: llm_predictions, rag_predictions, final_predictions
- **Process**: 5-case classification, update vector DB
- **Returns**: Updated KB + metrics

---

## Key Insight

**The "parallel" part is NOT semantic mapper || RAG API call.**

**The "parallel" part IS semantic mapper || headers extractor.**

**RAG API is called AFTER headers extractor completes**, using its output.

This is still beneficial because:
- Headers extractor takes ~8s (LLM calls for header classification)
- Semantic mapper takes ~5s (LLM calls for field mapping)
- Running both in parallel saves ~5s vs sequential
- RAG API call (~2s) happens after, uses headers output

---

**Document Version**: 1.0  
**Last Updated**: March 2, 2026  
**Status**: Final Corrected Version
