# Module Documentation: rag_lambda

## Overview
The `rag_lambda` module is an intelligent RAG (Retrieval-Augmented Generation) system that predicts PDF form field names using vector similarity search. It combines semantic embeddings with GPT-4 for field mapping, tracks prediction accuracy, processes user feedback, and maintains comprehensive analytics across the entire system.

## Purpose
- Generate RAG predictions for PDF form fields using vector similarity
- Track and compare RAG vs LLM predictions
- Process user feedback to improve field mapping accuracy
- Maintain vector database with confidence scoring
- Provide comprehensive analytics (PDF, category, global, error analysis)
- Support incremental learning from user corrections

## Architecture

### Entry Point
- **File**: `lambda_function.py`
- **Handler**: `lambda_handler(event, context)`
- **Type**: AWS Lambda with API key authentication

### Module Structure
```
rag_lambda/
├── lambda_function.py          # Entry point, API routing (523 lines)
├── api.py                      # API definitions
├── config/
│   └── settings.py             # Configuration, environment variables
├── services/
│   ├── prediction_service.py   # RAG prediction logic
│   ├── s3_service.py           # S3 operations
│   ├── case_classifier.py      # Prediction case classification
│   ├── metrics_service.py      # Metrics calculation
│   ├── feedback_processor.py   # User feedback processing
│   ├── time_series_service.py  # Time series analytics
│   ├── analytics_service.py    # Analytics aggregation
│   └── openai_service.py       # GPT-4 integration
├── models/
│   ├── embeddings.py           # Sentence Transformer embeddings
│   ├── predictor.py            # Field prediction logic
│   └── vector_manager.py       # Vector database management
└── utils/
    ├── helpers.py              # Utility functions
    └── constants.py            # Constants, case types
```

## API Endpoints

### API 1: get_rag_predictions
**Purpose**: Generate RAG predictions for PDF fields

**Payload**:
```json
{
  "api_name": "get_rag_predictions",
  "user_id": "user_77",
  "session_id": "session_991",
  "pdf_id": "pdf_001",
  "header_file_location": "s3://bucket/path/to/header_file.json"
}
```

**Process**:
1. Load header file (field list with context)
2. Generate submission ID (tracks duplicates)
3. For each field:
   - Generate embedding using Sentence Transformer
   - Search vector database for similar fields (top-k)
   - Calculate confidence score
   - Return best match or null
4. Save predictions to S3
5. Update PDF hash mapping (frequency tracking)

**Output**:
```json
{
  "status": "success",
  "message": "RAG predictions generated successfully",
  "data": {
    "user_id": "user_77",
    "session_id": "session_991",
    "pdf_id": "pdf_001",
    "submission_id": "sub_123",
    "pdf_hash": "abc123",
    "frequency": 1,
    "is_duplicate": false,
    "s3_paths": {
      "input": "s3://bucket/.../header_file.json",
      "rag_predictions": "s3://bucket/.../rag_predictions.json"
    },
    "summary": {
      "total_fields": 50,
      "predicted_fields": 45,
      "unpredicted_fields": 5,
      "avg_confidence": 0.87
    }
  }
}
```

### API 2: saving_filled_pdf
**Purpose**: Store filled PDF and process all prediction files

**Payload**:
```json
{
  "api_name": "saving_filled_pdf",
  "user_id": "user_77",
  "session_id": "session_991",
  "filled_doc_pdf_id": "pdf_001",
  "filled_pdf_location": "s3://bucket/path/to/filled.pdf"
}
```

**Prerequisites**:
- Backend must save before calling:
  - `llm_predictions.json` (LLM predictions)
  - `final_predictions.json` (user's final selections)

**Process**:
1. Copy filled PDF to storage
2. Load all 3 prediction files (RAG, LLM, final)
3. **Case Classification** (5 cases):
   - **CASE_A**: RAG = LLM = Final (both correct)
   - **CASE_B**: RAG ≠ LLM, user selected one (validation)
   - **CASE_C**: RAG only predicted (LLM missed)
   - **CASE_D**: LLM only predicted (RAG missed)
   - **CASE_E**: Neither predicted (both failed)
4. **Metrics Calculation**: Accuracy, precision, recall per model
5. **Vector Updates**: 
   - Boost confidence for correct predictions
   - Create new vectors from LLM when selected
   - Decay confidence for wrong predictions
6. **Time Series Updates**: 5 hierarchical levels
   - Global (all data)
   - Category (e.g., "finance")
   - Subcategory (e.g., "investment")
   - Document Type (e.g., "subscription_form")
   - PDF Hash (specific form)

**Output**:
```json
{
  "status": "success",
  "message": "Filled PDF stored and processing completed",
  "data": {
    "user_id": "user_77",
    "session_id": "session_991",
    "pdf_id": "pdf_001",
    "submission_id": "sub_123",
    "pdf_stored_at": "s3://bucket/.../filled.pdf",
    "processing_completed": true
  }
}
```

### API 4: user_feedback
**Purpose**: Process user feedback on errors

**Payload**:
```json
{
  "api_name": "user_feedback",
  "user_id": "user_77",
  "session_id": "session_991",
  "pdf_id": "pdf_001",
  "error_type": "wrong_field_name",
  "timestamp": "2026-03-02T10:30:00Z",
  "feedback": "Should be 'investor_full_legal_name'",
  "field_name": "investor_name",
  "field_type": "text",
  "page_number": 1,
  "value": "John Doe",
  "corners": [[100, 200], [300, 200], [300, 250], [100, 250]]
}
```

**Process**:
1. Load feedback JSONL file
2. For each error:
   - Use GPT-4 to standardize corrected field name
   - Create new vector with corrected mapping
   - Log error to analytics
   - Update error time series
3. Save feedback log
4. Return summary

**Output**:
```json
{
  "status": "success",
  "message": "Feedback processed successfully",
  "data": {
    "errors_processed": 1,
    "vectors_created": 1,
    "analytics_updated": true
  }
}
```

### API 5: get_metrics
**Purpose**: Retrieve comprehensive metrics

**Metric Types**:
1. **pdf**: Metrics for specific PDF
   ```json
   {
     "metric_type": "pdf",
     "user_id": "user_77",
     "session_id": "session_991",
     "pdf_id": "pdf_001"
   }
   ```

2. **category**: Aggregated metrics by category
   ```json
   {
     "metric_type": "category",
     "category": "finance"
   }
   ```

3. **subcategory**: Aggregated metrics by subcategory
   ```json
   {
     "metric_type": "subcategory",
     "category": "finance",
     "subcategory": "investment"
   }
   ```

4. **doctype**: Aggregated metrics by document type
   ```json
   {
     "metric_type": "doctype",
     "category": "finance",
     "subcategory": "investment",
     "doctype": "subscription_form"
   }
   ```

5. **global**: System-wide metrics
   ```json
   {
     "metric_type": "global"
   }
   ```

6. **compare**: Compare multiple PDFs
   ```json
   {
     "metric_type": "compare",
     "pdfs": [
       {"user_id": "u1", "session_id": "s1", "pdf_id": "p1"},
       {"user_id": "u2", "session_id": "s2", "pdf_id": "p2"}
     ]
   }
   ```

7. **pdf_hash**: All submissions for a specific form
   ```json
   {
     "metric_type": "pdf_hash",
     "pdf_hash": "abc123"
   }
   ```

**Output Example (Global Metrics)**:
```json
{
  "status": "success",
  "data": {
    "llm_metrics": {
      "total_predictions": 5000,
      "correct": 4500,
      "incorrect": 500,
      "accuracy": 0.90,
      "precision": 0.88,
      "recall": 0.92,
      "f1_score": 0.90
    },
    "rag_metrics": {
      "total_predictions": 5000,
      "correct": 4200,
      "incorrect": 800,
      "accuracy": 0.84,
      "precision": 0.82,
      "recall": 0.86,
      "f1_score": 0.84
    },
    "ensemble_metrics": {
      "total_predictions": 5000,
      "correct": 4700,
      "incorrect": 300,
      "accuracy": 0.94,
      "precision": 0.93,
      "recall": 0.95,
      "f1_score": 0.94
    },
    "llm_vs_rag": {
      "llm_wins": 300,
      "rag_wins": 200,
      "ties": 4500,
      "llm_win_rate": 0.60
    }
  }
}
```

### API 6: get_system_info
**Purpose**: Retrieve system overview

**Payload**:
```json
{
  "api_name": "get_system_info"
}
```

**Output**:
```json
{
  "status": "success",
  "data": {
    "summary": {
      "total_pdfs": 1000,
      "total_pdf_hashes": 50,
      "total_submissions": 1200,
      "unique_users": 100,
      "unique_sessions": 500,
      "total_categories": 5,
      "total_subcategories": 15,
      "total_document_types": 30,
      "total_vectors": 5000,
      "total_errors": 150
    },
    "users": ["user_1", "user_2", "..."],
    "sessions": ["session_1", "session_2", "..."],
    "pdf_hashes": {
      "abc123": {
        "submission_count": 25,
        "user_count": 10,
        "error_count": 5,
        "category": "finance",
        "subcategory": "investment",
        "document_type": "subscription_form"
      }
    },
    "categories": ["finance", "legal", "healthcare", "..."],
    "subcategories": {
      "finance": ["investment", "banking", "insurance"]
    },
    "document_types": {
      "finance.investment": ["subscription_form", "redemption_form"]
    },
    "vector_db": {
      "total_vectors": 5000,
      "by_source": {
        "rag": 3000,
        "llm": 1500,
        "manual": 500
      }
    }
  }
}
```

### API 7: get_error_analytics
**Purpose**: Analyze errors with filtering

**Payload**:
```json
{
  "api_name": "get_error_analytics",
  "date_from": "2026-02-01T00:00:00Z",
  "date_to": "2026-02-28T23:59:59Z",
  "category": "finance",
  "subcategory": "investment",
  "doctype": "subscription_form"
}
```

**Output**:
```json
{
  "status": "success",
  "data": {
    "filters_applied": {
      "date_from": "2026-02-01T00:00:00Z",
      "date_to": "2026-02-28T23:59:59Z",
      "category": "finance",
      "subcategory": "investment",
      "doctype": "subscription_form"
    },
    "total_errors": 45,
    "breakdown": {
      "by_category": {
        "finance": 45
      },
      "by_subcategory": {
        "investment": 45
      },
      "by_doctype": {
        "subscription_form": 45
      },
      "by_date": {
        "2026-02-05": 10,
        "2026-02-10": 15,
        "2026-02-20": 20
      },
      "by_error_type": {
        "wrong_field_name": 30,
        "missing_field": 10,
        "wrong_value": 5
      },
      "by_case_type": {
        "CASE_B": 25,
        "CASE_E": 20
      }
    },
    "errors": [
      {
        "user_id": "user_77",
        "session_id": "session_991",
        "pdf_id": "pdf_001",
        "error_type": "wrong_field_name",
        "field_name": "investor_name",
        "corrected_field_name": "investor_full_legal_name",
        "timestamp": "2026-02-05T10:30:00Z",
        "case_type": "CASE_B"
      }
    ]
  }
}
```

## Key Components

### 1. Embedding Generation (`models/embeddings.py`)
- **Model**: Sentence Transformer (`all-MiniLM-L6-v2`)
- **Purpose**: Convert field context to semantic embeddings
- **Process**:
  1. Combine field context, section context, headers
  2. Generate 384-dimensional embedding vector
  3. Support batch processing for efficiency

### 2. Vector Database (`models/vector_manager.py`)
- **Storage**: S3-based vector index
- **Features**:
  - Cosine similarity search
  - Confidence scoring (0.50 - 0.99)
  - Top-k retrieval
  - Ambiguity detection (similarity margin < threshold)
- **Updates**:
  - **Positive feedback**: Confidence × 1.05 (growth rate)
  - **Negative feedback**: Confidence × 0.95 (decay rate)
  - **Max confidence**: 0.99 (prevents overconfidence)
  - **Min confidence**: 0.50 (prevents removal)

### 3. Case Classification (`services/case_classifier.py`)
**5 Prediction Cases**:

| Case | RAG | LLM | Final | Meaning |
|------|-----|-----|-------|---------|
| **CASE_A** | ✅ | ✅ | ✅ | Both correct (same prediction) |
| **CASE_B** | ✅ | ✅ | One selected | Both predicted, user chose one |
| **CASE_C** | ✅ | ❌ | RAG | Only RAG predicted (LLM missed) |
| **CASE_D** | ❌ | ✅ | LLM | Only LLM predicted (RAG missed) |
| **CASE_E** | ❌ | ❌ | Manual | Neither predicted (both failed) |

### 4. Metrics Calculation (`services/metrics_service.py`)
**Metrics Per Model**:
- **Accuracy**: (Correct predictions) / (Total predictions)
- **Precision**: (True positives) / (True positives + False positives)
- **Recall**: (True positives) / (True positives + False negatives)
- **F1 Score**: 2 × (Precision × Recall) / (Precision + Recall)

**Ensemble Metrics**:
- Combined RAG + LLM performance
- Model agreement rate
- Confidence-weighted accuracy

### 5. Feedback Processing (`services/feedback_processor.py`)
**Process**:
1. **GPT-4 Standardization**: Convert user feedback to standard field names
2. **Vector Creation**: Generate embedding for corrected field
3. **Confidence Initialization**: Set initial confidence (0.80)
4. **Error Logging**: Track error type, timestamp, metadata
5. **Analytics Update**: Update time series and error breakdown

### 6. Time Series Analytics (`services/time_series_service.py`)
**5 Hierarchical Levels**:
1. **Global**: All predictions across system
2. **Category**: e.g., "finance" (all subcategories)
3. **Subcategory**: e.g., "investment" (all document types)
4. **Document Type**: e.g., "subscription_form" (all hashes)
5. **PDF Hash**: Specific form (all submissions)

**Tracked Metrics**:
- Daily prediction counts
- Accuracy trends
- Error rates
- Confidence distributions
- Model comparisons (RAG vs LLM)

## Environment Variables

### Required
| Variable | Description | Example |
|----------|-------------|---------|
| `X_API_KEY` | API key for authentication | `secret-key` |
| `S3_BUCKET` | S3 bucket for RAG data | `rag-bucket-pdf-filler` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |

### Optional (Model Configuration)
| Variable | Description | Default |
|----------|-------------|---------|
| `GPT4_MODEL` | GPT-4 model name | `gpt-4-turbo-preview` |
| `GPT4_TEMPERATURE` | GPT-4 temperature | `0.3` |
| `GPT4_MAX_TOKENS` | GPT-4 max tokens | `500` |
| `EMBEDDING_MODEL` | Embedding model type | `sentence-transformer` |
| `ST_MODEL_NAME` | Sentence Transformer model | `all-MiniLM-L6-v2` |

### Optional (Prediction Configuration)
| Variable | Description | Default |
|----------|-------------|---------|
| `PREDICTION_THRESHOLD` | Minimum confidence | `0.75` |
| `CONFIDENCE_DECAY_RATE` | Negative feedback multiplier | `0.95` |
| `CONFIDENCE_GROWTH_RATE` | Positive feedback multiplier | `1.05` |
| `MAX_CONFIDENCE` | Maximum confidence cap | `0.99` |
| `MIN_CONFIDENCE` | Minimum confidence floor | `0.50` |
| `AMBIGUITY_THRESHOLD` | Similarity margin threshold | `0.10` |
| `TOP_K` | Number of similar vectors | `5` |

### Optional (Integration)
| Variable | Description | Default |
|----------|-------------|---------|
| `RAG_LAMBDA_FUNCTION_NAME` | Lambda function name | N/A |
| `BACKEND_API_ENDPOINT` | Backend API URL | N/A |
| `BACKEND_AUTH_TOKEN` | Backend auth token | N/A |

## Hardcoded Dependencies (Requiring Refactoring)

### 🔴 LLM Provider (CRITICAL)
**Location**: `services/openai_service.py` lines 3-4, 12

```python
from openai import OpenAI                                  # ❌ HARDCODED
from config.settings import OPENAI_API_KEY, GPT4_MODEL, GPT4_TEMPERATURE, GPT4_MAX_TOKENS

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)      # ❌ HARDCODED
    
    def generate_corrected_field_name(self, error_data):
        response = self.client.chat.completions.create(
            model=GPT4_MODEL,                              # ❌ CONFIGURABLE BUT OPENAI-SPECIFIC
            temperature=GPT4_TEMPERATURE,
            max_tokens=GPT4_MAX_TOKENS
        )
```

**Additional Locations**:
- `config/settings.py` lines 11-15: OpenAI configuration

**Issues**:
- Only supports OpenAI API
- No support for Anthropic Claude, Azure OpenAI, AWS Bedrock
- Model is configurable but still OpenAI-specific
- API client is hardcoded to OpenAI SDK

**Refactoring Required**:
1. Create LLM provider abstraction layer
2. Support multiple providers (OpenAI, Anthropic, Azure, Bedrock)
3. Provider-agnostic configuration
4. Example:
   ```python
   LLM_PROVIDER = "openai"  # or "anthropic", "azure", "bedrock"
   LLM_MODEL = "gpt-4-turbo-preview"
   LLM_TEMPERATURE = 0.3
   ```

### 🔴 Embedding Model (CRITICAL)
**Location**: `models/embeddings.py` lines 3-4, 23-25

```python
from sentence_transformers import SentenceTransformer      # ❌ HARDCODED
from config.settings import EMBEDDING_MODEL, ST_MODEL_NAME

class EmbeddingGenerator:
    def __init__(self):
        if self._model is None:
            if EMBEDDING_MODEL == "sentence-transformer":  # ❌ HARDCODED
                self._model = SentenceTransformer(ST_MODEL_NAME)  # ❌ HARDCODED
                logger.info(f"Loaded Sentence Transformer: {ST_MODEL_NAME}")
```

**Additional Locations**:
- `config/settings.py` lines 17-18: Embedding configuration

**Issues**:
- Only supports Sentence Transformers (Hugging Face)
- No support for OpenAI embeddings, Cohere, Voyage AI
- Model name is configurable but framework is hardcoded
- Cannot switch to proprietary embedding APIs

**Refactoring Required**:
1. Create embedding provider abstraction layer
2. Support multiple providers (Sentence Transformers, OpenAI, Cohere, Voyage)
3. Provider-agnostic interface
4. Example:
   ```python
   EMBEDDING_PROVIDER = "sentence-transformer"  # or "openai", "cohere", "voyage"
   EMBEDDING_MODEL = "all-MiniLM-L6-v2"
   EMBEDDING_DIMENSION = 384
   ```

### 🔴 Storage Provider (CRITICAL)
**Location**: `services/s3_service.py` lines 2-3, 10

```python
import boto3                                               # ❌ AWS-SPECIFIC
from config.settings import S3_BUCKET

s3_client = boto3.client('s3')                            # ❌ HARDCODED

class S3Service:
    def __init__(self):
        self.S3_BUCKET = S3_BUCKET                        # ❌ S3-SPECIFIC
    
    def save_json(self, s3_key, data):
        s3_client.put_object(                             # ❌ S3-SPECIFIC
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=json.dumps(data, indent=2).encode('utf-8'),
            ContentType='application/json'
        )
```

**Additional Locations**:
- `config/settings.py` line 4: S3 bucket configuration
- All S3 operations throughout codebase

**Issues**:
- All storage operations assume AWS S3
- Uses boto3 client (AWS-specific)
- No support for Azure Blob Storage, Google Cloud Storage
- S3 bucket name and key patterns are hardcoded

**Refactoring Required**:
1. Create storage provider abstraction layer
2. Support multiple providers (S3, Azure Blob, GCS, local)
3. Provider-agnostic configuration
4. Example:
   ```python
   STORAGE_PROVIDER = "s3"  # or "azure_blob", "gcs", "local"
   STORAGE_BUCKET = "rag-bucket-pdf-filler"
   ```

### 🟡 Vector Database (MEDIUM)
**Location**: `models/vector_manager.py` (implied, not fully visible)

**Issues**:
- Currently S3-based (custom implementation)
- No support for dedicated vector databases (Pinecone, Weaviate, Qdrant, ChromaDB)
- Limited scalability for large vector collections
- Manual similarity search (not optimized)

**Refactoring Required**:
1. Create vector database abstraction layer
2. Support dedicated vector DBs (Pinecone, Weaviate, Qdrant, ChromaDB, FAISS)
3. Maintain S3-based option for simplicity
4. Example:
   ```python
   VECTOR_DB_PROVIDER = "s3"  # or "pinecone", "weaviate", "qdrant", "chromadb"
   VECTOR_DB_DIMENSION = 384
   VECTOR_DB_METRIC = "cosine"
   ```

### 🟡 Backend API Dependency (MEDIUM)
**Location**: `config/settings.py` lines 8-9

```python
BACKEND_API_ENDPOINT = os.getenv("BACKEND_API_ENDPOINT")  # ❌ DIRECT COUPLING
BACKEND_AUTH_TOKEN = os.getenv("BACKEND_AUTH_TOKEN")
```

**Issues**:
- Tightly coupled to specific backend API
- No abstraction for different authentication methods
- Hardcoded API communication pattern

**Refactoring Required**:
1. Create backend client abstraction
2. Support multiple authentication methods (Bearer token, API key, IAM)
3. Make endpoints configurable

## S3 Data Structure

### Predictions Folder
```
s3://rag-bucket-pdf-filler/
├── predictions/
│   └── {user_id}/
│       └── {session_id}/
│           └── {pdf_id}/
│               ├── metadata/
│               │   ├── submission_info.json
│               │   └── pdf_info.json
│               ├── predictions/
│               │   ├── rag_predictions.json
│               │   ├── llm_predictions.json
│               │   └── final_predictions.json
│               └── analysis/
│                   ├── case_classification.json
│                   ├── metrics_snapshot.json
│                   └── vector_update_summary.json
```

### Time Series Folder
```
s3://rag-bucket-pdf-filler/
├── time_series/
│   ├── global/
│   │   └── metrics_daily.json
│   ├── category/
│   │   └── {category}/
│   │       └── metrics_daily.json
│   ├── subcategory/
│   │   └── {category}/
│   │       └── {subcategory}/
│   │           └── metrics_daily.json
│   ├── doctype/
│   │   └── {category}/
│   │       └── {subcategory}/
│   │           └── {doctype}/
│   │               └── metrics_daily.json
│   └── pdf_hash/
│       └── {pdf_hash}/
│           └── metrics_daily.json
```

### Feedback Folder
```
s3://rag-bucket-pdf-filler/
├── user_feedbacks/
│   └── {user_id}/
│       └── {session_id}/
│           └── {pdf_id}/
│               └── feedback.jsonl
```

### Vector Database Folder
```
s3://rag-bucket-pdf-filler/
├── vector_db/
│   ├── vectors.json
│   ├── index.json
│   └── metadata.json
```

### PDF Hash Registry
```
s3://rag-bucket-pdf-filler/
├── pdf_hash_registry/
│   └── {pdf_hash}/
│       └── submissions.json
```

## Workflow Diagrams

### RAG Prediction Flow
```
┌─────────────────────────────────────────────────────────────┐
│               RAG PREDICTION WORKFLOW                        │
└─────────────────────────────────────────────────────────────┘

  1. API 1: get_rag_predictions
      │
      ├──→ Load header_file.json
      │    - pdf_hash
      │    - pdf_category
      │    - fields[] with context
      │
      ├──→ Generate submission ID
      │    - Check PDF hash registry
      │    - Track frequency
      │    - Detect duplicates
      │
      └──→ For each field:
           │
           ├──→ Create embedding
           │    - Combine context + section + headers
           │    - Generate 384-dim vector
           │
           ├──→ Vector similarity search
           │    - Top-k retrieval (default: 5)
           │    - Cosine similarity
           │    - Apply threshold (0.75)
           │
           ├──→ Ambiguity check
           │    - Compare top 2 similarities
           │    - Flag if margin < 0.10
           │
           └──→ Return prediction
                - Matched: field name + confidence
                - Unmatched: null
      │
      └──→ Save rag_predictions.json
      │
      └──→ Update PDF hash mapping
```

### PDF Processing Flow
```
┌─────────────────────────────────────────────────────────────┐
│               PDF PROCESSING WORKFLOW                        │
└─────────────────────────────────────────────────────────────┘

  2. API 2: saving_filled_pdf
      │
      ├──→ Copy filled PDF to storage
      │
      ├──→ Load 3 prediction files
      │    - rag_predictions.json
      │    - llm_predictions.json
      │    - final_predictions.json
      │
      ├──→ Case Classification
      │    │
      │    ├──→ CASE_A: RAG = LLM = Final
      │    │    - Both correct
      │    │    - Boost RAG confidence
      │    │
      │    ├──→ CASE_B: RAG ≠ LLM, user selected
      │    │    - Boost selected model confidence
      │    │    - Decay rejected model confidence
      │    │    - Create vector from LLM if selected
      │    │
      │    ├──→ CASE_C: RAG only
      │    │    - RAG success, LLM failure
      │    │    - Boost RAG confidence
      │    │
      │    ├──→ CASE_D: LLM only
      │    │    - LLM success, RAG failure
      │    │    - Create vector from LLM
      │    │
      │    └──→ CASE_E: Neither predicted
      │         - Both failed
      │         - Manual entry required
      │
      ├──→ Metrics Calculation
      │    - Accuracy, precision, recall per model
      │    - Ensemble metrics
      │    - LLM vs RAG comparison
      │
      ├──→ Vector Updates
      │    - Update existing vectors (confidence)
      │    - Create new vectors (from LLM)
      │    - Apply decay/growth rates
      │
      └──→ Time Series Updates
           - Global metrics
           - Category metrics
           - Subcategory metrics
           - Document type metrics
           - PDF hash metrics
```

### Feedback Processing Flow
```
┌─────────────────────────────────────────────────────────────┐
│             FEEDBACK PROCESSING WORKFLOW                     │
└─────────────────────────────────────────────────────────────┘

  4. API 4: user_feedback
      │
      ├──→ Load feedback.jsonl
      │
      └──→ For each error:
           │
           ├──→ GPT-4 Standardization
           │    - Analyze error context
           │    - Generate standardized field name
           │    - Snake_case convention
           │    - Return confidence + reasoning
           │
           ├──→ Create New Vector
           │    - Generate embedding for corrected field
           │    - Initial confidence: 0.80
           │    - Source: "manual" (user feedback)
           │    - Add to vector database
           │
           ├──→ Log Error Analytics
           │    - Track error type
           │    - Category/subcategory/doctype
           │    - Timestamp
           │    - Case type (from classification)
           │
           └──→ Update Time Series
                - Increment error count
                - Update error breakdown
                - Track by date
```

## Performance Considerations

### Embedding Generation
- **Cold start**: 5-10s (model loading)
- **Warm execution**: 50-200ms per field
- **Batch processing**: More efficient for multiple fields

### Vector Search
- **Search latency**: 100-500ms (depends on vector count)
- **Top-k retrieval**: Linear scan (no indexing)
- **Scalability**: Limited by S3 read/write

### GPT-4 Calls
- **Per error**: 2-5s
- **Cost**: ~$0.01 per feedback item
- **Fallback**: Regex cleanup if GPT-4 fails

### Metrics Calculation
- **Per PDF**: 500ms-2s
- **Global metrics**: 5-10s
- **Time series updates**: 2-5s per level

## Integration Points

### Upstream Dependencies
- **Main Pipeline**: Provides header_file.json and llm_predictions.json
- **S3**: Storage for all data files
- **OpenAI API**: GPT-4 for field name standardization
- **Sentence Transformers**: Embedding generation

### Downstream Dependencies
- **S3**: Storage for predictions, metrics, analytics
- **Backend API** (optional): Can send notifications

## Known Limitations

1. **Embedding Model Locked**: Cannot switch to other embedding providers without code changes
2. **S3-Based Vector DB**: Limited scalability, no optimized indexing
3. **Linear Search**: O(n) complexity for vector similarity (slow for large datasets)
4. **GPT-4 Dependency**: Cannot use other LLMs for field standardization
5. **No Batch API Support**: Processes PDFs one at a time
6. **No Real-Time Updates**: Vector database requires full rebuild
7. **Limited Error Recovery**: If case classification fails, entire pipeline fails
8. **No Versioning**: Vector updates overwrite, no rollback capability
9. **S3 Consistency**: Eventual consistency can cause race conditions
10. **Cold Start**: Sentence Transformer loading adds 5-10s latency

## Refactoring Roadmap

### Phase 1: Configuration Externalization
- Move all hardcoded values to environment variables
- Create configuration schema
- Add validation layer

### Phase 2: LLM Provider Abstraction
- Create `LLMProvider` interface
- Implement OpenAI, Anthropic, Azure providers
- Make provider configurable

### Phase 3: Embedding Provider Abstraction
- Create `EmbeddingProvider` interface
- Implement Sentence Transformers, OpenAI, Cohere providers
- Support model switching

### Phase 4: Vector Database Migration
- Evaluate dedicated vector databases (Pinecone, Weaviate, Qdrant)
- Implement vector DB abstraction layer
- Support multiple providers
- Add HNSW or IVF indexing for faster search

### Phase 5: Storage Provider Abstraction
- Create `StorageProvider` interface
- Implement S3, Azure Blob, GCS providers
- Unify data structure across providers

### Phase 6: Real-Time Processing
- Implement streaming updates
- Add event-driven architecture (SQS, EventBridge)
- Support incremental vector updates

### Phase 7: Monitoring & Observability
- Add distributed tracing (X-Ray)
- Implement structured logging
- Create dashboards for metrics
- Add alerting for anomalies

## Related Modules

### Main Pipeline (`src/`)
- Provides: header_file.json, llm_predictions.json
- Dependency: This module receives predictions from main pipeline

### pdf_upload_lambda (Previously Documented)
- Purpose: Process uploaded PDFs
- Integration: Calls main pipeline for predictions

### chatbot_lambda (Previously Documented)
- Purpose: Conversational form filling
- Integration: Calls main pipeline for PDF operations

---

**Last Updated**: 2026-03-02
**Version**: 1.0.0
**Maintainer**: Development Team
