# PDF Autofillr - System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PDF AUTOFILLR PLATFORM                              │
│                                                                              │
│  "Intelligent PDF Form Filling with AI-Powered Field Mapping"               │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: CLIENT INTERFACES                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Python SDK   │  │ TypeScript   │  │ CLI Tool     │  │ REST API     │   │
│  │              │  │ SDK          │  │              │  │              │   │
│  │ pip install  │  │ npm install  │  │ pdf-autofill │  │ curl/HTTP    │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                  │                  │                  │           │
│         └──────────────────┴──────────────────┴──────────────────┘           │
│                                     │                                        │
│                                     │ HTTP/HTTPS                            │
│                                     ▼                                        │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: API GATEWAY / ROUTING                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │  FastAPI Server (Local) / API Gateway (Cloud)                      │    │
│  │  • Authentication & Authorization                                   │    │
│  │  • Rate Limiting                                                    │    │
│  │  • Request Validation                                               │    │
│  │  • Response Formatting                                              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                     │                                        │
└─────────────────────────────────────┼────────────────────────────────────────┘
                                      │
                                      ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: CORE MODULES (Business Logic)                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      MAPPER MODULE (Core Engine)                      │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │  │
│  │  │ EXTRACTOR   │→ │  MAPPER     │→ │  EMBEDDER   │→ │  FILLER    │ │  │
│  │  │             │  │             │  │             │  │            │ │  │
│  │  │ • PyMuPDF   │  │ • LiteLLM   │  │ • Metadata  │  │ • PyMuPDF  │ │  │
│  │  │ • Fields    │  │ • Semantic  │  │ • JSON      │  │ • XFA      │ │  │
│  │  │ • Widgets   │  │ • Matching  │  │ • Embed     │  │ • AcroForm │ │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │  │
│  │                                                                       │  │
│  │  Supporting Components:                                               │  │
│  │  • Chunkers    → Split PDFs for processing                          │  │
│  │  • Groupers    → Group related fields                               │  │
│  │  • Headers     → Detect document structure                          │  │
│  │  • Validators  → Validate field values                              │  │
│  │  • Cache       → Hash-based PDF caching                             │  │
│  │                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐   │
│  │ CHATBOT MODULE     │  │ RAG MODULE         │  │ PDF UPLOAD MODULE  │   │
│  ├────────────────────┤  ├────────────────────┤  ├────────────────────┤   │
│  │                    │  │                    │  │                    │   │
│  │ • State Machine    │  │ • Vector DB        │  │ • S3/Azure/GCS     │   │
│  │ • NLU              │  │ • Embeddings       │  │ • File Validation  │   │
│  │ • Conversation     │  │ • Retrieval        │  │ • URL Generation   │   │
│  │ • LLM Extraction   │  │ • Context Boost    │  │ • Metadata Track   │   │
│  │ • Session State    │  │ • Confidence       │  │                    │   │
│  │                    │  │                    │  │                    │   │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘   │
│           │                       │                       │                 │
│           └───────────────────────┴───────────────────────┘                 │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼

┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: EXTERNAL SERVICES                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ LLM Providers│  │ Cloud Storage│  │ Notifications│  │ Monitoring   │   │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤  ├──────────────┤   │
│  │              │  │              │  │              │  │              │   │
│  │ • OpenAI     │  │ • AWS S3     │  │ • MS Teams   │  │ • CloudWatch │   │
│  │ • Anthropic  │  │ • Azure Blob │  │ • Slack      │  │ • App Insights│  │
│  │ • Bedrock    │  │ • GCS        │  │ • Email      │  │ • Stackdriver│   │
│  │ • Azure OAI  │  │ • Local FS   │  │ • Webhooks   │  │ • Custom     │   │
│  │ • Vertex AI  │  │              │  │              │  │              │   │
│  │              │  │              │  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: PDF Processing Pipeline

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        PDF PROCESSING FLOW                                │
└──────────────────────────────────────────────────────────────────────────┘

INPUT: Raw PDF Form
    │
    ▼
┌─────────────────────────┐
│  1. EXTRACTION          │
│  • Parse PDF structure  │
│  • Find form fields     │
│  • Extract widgets      │
│  • Get coordinates      │
└────────┬────────────────┘
         │
         │ Output: Extracted Fields JSON
         │ {
         │   "field_1": {"type": "text", "coords": [...]},
         │   "field_2": {"type": "checkbox", ...}
         │ }
         │
         ▼
┌─────────────────────────┐
│  2. MAPPING             │
│  • Send to LLM          │
│  • Semantic matching    │
│  • Confidence scoring   │
│  • RAG enhancement (opt)│
└────────┬────────────────┘
         │
         │ Output: Mapping JSON
         │ {
         │   "field_1": {"mapped_to": "user.firstName"},
         │   "field_2": {"mapped_to": "terms.accepted"}
         │ }
         │
         ▼
┌─────────────────────────┐
│  3. EMBEDDING           │
│  • Inject metadata      │
│  • Store in PDF         │
│  • Preserve original    │
└────────┬────────────────┘
         │
         │ Output: Embedded PDF (reusable!)
         │
         ▼
┌─────────────────────────┐
│  4. FILLING             │
│  • Read metadata        │
│  • Apply data values    │
│  • Generate filled PDF  │
└────────┬────────────────┘
         │
         ▼
OUTPUT: Filled PDF Form ✅
```

---

## Module Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       MODULE INTERACTIONS                                │
└─────────────────────────────────────────────────────────────────────────┘


    ┌─────────────┐
    │   CLIENT    │
    │  (SDK/CLI)  │
    └──────┬──────┘
           │
           │ HTTP Request
           │
           ▼
    ┌─────────────┐
    │ API GATEWAY │
    └──────┬──────┘
           │
           ├─────────────────┬─────────────────┬─────────────────┐
           │                 │                 │                 │
           ▼                 ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐    ┌──────────┐      ┌──────────┐
    │  MAPPER  │◄────►│ RAG      │    │ CHATBOT  │◄────►│  UPLOAD  │
    │  MODULE  │      │ MODULE   │    │ MODULE   │      │  MODULE  │
    └────┬─────┘      └──────────┘    └────┬─────┘      └──────────┘
         │                                   │
         │                                   │
         └───────────────┬───────────────────┘
                         │
                         │ Calls
                         │
                         ▼
              ┌─────────────────────┐
              │  EXTERNAL SERVICES  │
              │  • LLM APIs         │
              │  • Cloud Storage    │
              │  • Notifications    │
              └─────────────────────┘


Interaction Patterns:

1. SDK → Mapper
   Direct API calls for PDF operations

2. Chatbot → Mapper
   Chatbot collects data, then calls Mapper to generate PDFs

3. Mapper ↔ RAG
   Parallel processing: Mapper uses RAG for enhanced accuracy

4. Upload → Mapper
   Upload stores PDF, Mapper processes it

5. All → Storage
   All modules can read/write to cloud storage

6. All → LLM
   Multiple modules use LLM for different purposes
```

---

## Deployment Architectures

### A. Local Development

```
┌─────────────────────────────────────────────────────────┐
│  Developer's Laptop                                      │
│                                                          │
│  ┌──────────────────────────────────────────────┐      │
│  │  Terminal 1: API Server                      │      │
│  │  $ cd modules/mapper                         │      │
│  │  $ python api_server.py                      │      │
│  │  → http://localhost:8000                     │      │
│  └──────────────────────────────────────────────┘      │
│                                                          │
│  ┌──────────────────────────────────────────────┐      │
│  │  Terminal 2: SDK/CLI                         │      │
│  │  $ pdf-autofiller extract input.pdf          │      │
│  │  → Calls http://localhost:8000               │      │
│  └──────────────────────────────────────────────┘      │
│                                                          │
│  Storage: Local filesystem                              │
│  LLM: Direct API calls (OpenAI/Claude)                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### B. AWS Serverless

```
┌──────────────────────────────────────────────────────────────┐
│  AWS Cloud                                                    │
│                                                               │
│  ┌─────────────────┐         ┌──────────────────┐           │
│  │  API Gateway    │────────▶│  Lambda          │           │
│  │  (REST API)     │         │  (Mapper Module) │           │
│  └─────────────────┘         └────────┬─────────┘           │
│                                        │                      │
│                              ┌─────────┴─────────┐           │
│                              │                   │           │
│                              ▼                   ▼           │
│                    ┌──────────────┐   ┌──────────────┐      │
│                    │  S3 Bucket   │   │  DynamoDB    │      │
│                    │  (PDFs)      │   │  (Metadata)  │      │
│                    └──────────────┘   └──────────────┘      │
│                                                               │
│  ┌────────────────────────────────────────────────┐         │
│  │  Client (anywhere)                              │         │
│  │  $ pdf-autofiller --api-url https://...       │         │
│  └────────────────────────────────────────────────┘         │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### C. Docker Container

```
┌──────────────────────────────────────────────────────────────┐
│  Docker Host                                                  │
│                                                               │
│  ┌─────────────────────────────────────────────────┐        │
│  │  Docker Container: pdf-autofiller               │        │
│  │                                                  │        │
│  │  ┌────────────────────────────────────┐        │        │
│  │  │  FastAPI Server                     │        │        │
│  │  │  Port: 8000                         │        │        │
│  │  └────────────────────────────────────┘        │        │
│  │                                                  │        │
│  │  Volumes:                                        │        │
│  │  • /data → /app/data (PDFs)                    │        │
│  │  • /.env → /app/.env (config)                  │        │
│  │                                                  │        │
│  └─────────────────────────────────────────────────┘        │
│                          │                                   │
│                          │ Exposed Port 8000                │
│                          ▼                                   │
│              External Access via :8000                       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND / CLIENT                                            │
├─────────────────────────────────────────────────────────────┤
│ • Python 3.8+       → SDK, CLI, Server                      │
│ • TypeScript/Node   → SDK (planned)                         │
│ • Rich              → CLI output                            │
│ • HTTPX/Requests    → HTTP clients                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BACKEND / SERVER                                             │
├─────────────────────────────────────────────────────────────┤
│ • FastAPI           → REST API framework                    │
│ • Uvicorn           → ASGI server                           │
│ • Pydantic          → Data validation                       │
│ • PyMuPDF (fitz)    → PDF processing                        │
│ • LiteLLM           → Unified LLM interface                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ AI / ML                                                      │
├─────────────────────────────────────────────────────────────┤
│ • OpenAI GPT-4      → Semantic mapping                      │
│ • Anthropic Claude  → Alternative LLM                       │
│ • AWS Bedrock       → Cloud LLM                             │
│ • Azure OpenAI      → Enterprise LLM                        │
│ • Embeddings        → Vector search (RAG)                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ STORAGE                                                      │
├─────────────────────────────────────────────────────────────┤
│ • AWS S3            → Cloud object storage                  │
│ • Azure Blob        → Cloud storage                         │
│ • Google GCS        → Cloud storage                         │
│ • Local Filesystem  → Development                           │
│ • DynamoDB/Cosmos   → Metadata (optional)                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE                                               │
├─────────────────────────────────────────────────────────────┤
│ • AWS Lambda        → Serverless compute                    │
│ • API Gateway       → API management                        │
│ • Docker            → Containerization                      │
│ • CloudWatch        → Monitoring                            │
│ • GitHub Actions    → CI/CD                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ SECURITY LAYERS                                              │
└─────────────────────────────────────────────────────────────┘

LAYER 1: Authentication
  • API Keys (X-API-Key header)
  • AWS IAM (for Lambda)
  • OAuth 2.0 (planned)

LAYER 2: Authorization
  • User ID validation
  • Document ownership checks
  • Role-based access (planned)

LAYER 3: Data Protection
  • TLS/HTTPS in transit
  • Encryption at rest (S3, Azure, GCS)
  • Environment variables for secrets
  • No credentials in code

LAYER 4: Input Validation
  • PDF file type validation
  • Size limits
  • Malware scanning (planned)
  • XSS/injection prevention

LAYER 5: Monitoring
  • Audit logs
  • Error tracking
  • Usage analytics
  • Anomaly detection (planned)
```

---

## Scalability Design

```
┌─────────────────────────────────────────────────────────────┐
│ SCALING STRATEGIES                                           │
└─────────────────────────────────────────────────────────────┘

HORIZONTAL SCALING
  • Stateless API servers
  • Load balancing
  • Auto-scaling groups
  • Lambda concurrency

VERTICAL SCALING
  • Memory configuration
  • CPU allocation
  • Timeout settings

CACHING
  • PDF hash-based caching (95% hit rate)
  • Mapping result caching
  • CDN for static assets

OPTIMIZATION
  • Async processing
  • Parallel chunking
  • Batch operations
  • Connection pooling

QUEUE SYSTEMS (Planned)
  • SQS/RabbitMQ for long-running jobs
  • Background processing
  • Rate limiting
```

---

## Key Design Decisions

### 1. Why Embed Metadata in PDFs?
**Decision:** Store mapping metadata inside the PDF itself  
**Reason:** 
- No database required
- Portable (PDF + data = filled form)
- Reusable across systems
- Faster subsequent fills

### 2. Why LiteLLM?
**Decision:** Use LiteLLM for unified LLM access  
**Reason:**
- Single interface for all providers
- Easy provider switching
- Fallback support
- Cost optimization

### 3. Why Hash-Based Caching?
**Decision:** Cache by PDF structural hash  
**Reason:**
- Same form structure = reuse results
- 95%+ speed improvement
- Storage efficient
- Automatic invalidation on changes

### 4. Why Multi-Cloud Support?
**Decision:** Support AWS, Azure, GCP, and local  
**Reason:**
- Customer flexibility
- Vendor lock-in avoidance
- Hybrid deployments
- Cost optimization

### 5. Why FastAPI?
**Decision:** Use FastAPI for REST API  
**Reason:**
- Modern async support
- Automatic API docs
- Type validation
- High performance

---

## Future Architecture Plans

```
PLANNED ENHANCEMENTS

1. Web Dashboard
   • Visual form builder
   • Mapping editor
   • Analytics dashboard

2. Webhook System
   • Event notifications
   • Integration platform
   • Custom workflows

3. Batch Processing
   • Bulk PDF processing
   • Queue management
   • Progress tracking

4. Advanced Caching
   • Redis integration
   • Distributed cache
   • Cache warming

5. Multi-Tenancy
   • Organization support
   • Team collaboration
   • Permission system

6. Audit System
   • Detailed logging
   • Compliance tracking
   • Data lineage
```

---

For detailed implementation, see individual module documentation.
