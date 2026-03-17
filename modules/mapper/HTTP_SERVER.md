# PDF Autofiller HTTP Server

REST API server for the PDF Autofiller Mapper module.

## Quick Start

### 1. Install Dependencies

```bash
cd modules/mapper
pip install fastapi uvicorn
```

### 2. Start the Server

```bash
python -m entrypoints.http_server
```

The server will start on `http://localhost:8000`

### 3. Test the API

**Option A: Use the test script**
```bash
python test_http_api.py
```

**Option B: Use curl**
```bash
# Health check
curl http://localhost:8000/health

# Make embed file
curl -X POST http://localhost:8000/make-embed-file \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 553,
    "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
    "pdf_doc_id": 990,
    "investor_type": "individual",
    "use_second_mapper": true
  }'
```

**Option C: View Interactive API Docs**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## API Endpoints

### Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "storage_type": "local"
}
```

### Make Embed File (Full Pipeline)
```
POST /make-embed-file
```

Request:
```json
{
  "user_id": 553,
  "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
  "pdf_doc_id": 990,
  "investor_type": "individual",
  "use_second_mapper": true
}
```

Response:
```json
{
  "status": "success",
  "operation": "make_embed_file",
  "output_paths": {
    "extracted_json": "/path/to/extracted.json",
    "mapping_json": "/path/to/mapping.json",
    "embedded_pdf": "/path/to/embedded.pdf",
    "llm_predictions": "/path/to/llm_predictions.json",
    "rag_predictions": "/path/to/rag_predictions.json"
  },
  "metadata": {
    "timing": {...},
    "cache_hit": false,
    "dual_mapper_info": {...}
  }
}
```

### Extract
```
POST /extract
```

Extracts text and form fields from PDF.

### Map
```
POST /map
```

Maps extracted fields to investor data schema.

### Embed
```
POST /embed
```

Embeds field mappings into PDF form fields.

### Fill
```
POST /fill
```

Fills PDF with provided data.

Request:
```json
{
  "user_id": 553,
  "session_id": "...",
  "pdf_doc_id": 990,
  "data": {
    "field_name": "field_value",
    ...
  }
}
```

---

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Server configuration
HTTP_HOST=0.0.0.0        # Default: 0.0.0.0
HTTP_PORT=8000           # Default: 8000

# Storage configuration (from config.ini)
STORAGE_TYPE=local       # local, aws, azure, gcp
DATA_DIR=/app/data       # Base data directory
```

### File Paths

The server uses the same file path patterns from `config.ini` as the CLI entrypoint.

**Input files:**
- PDF: `{data_dir}/input/{user_id}_{session_id}_{pdf_doc_id}_input.pdf`
- JSON: `{data_dir}/input/{user_id}_{session_id}_{pdf_doc_id}_input.json`

**Output files:**
- Results saved to: `{data_dir}/output/`

---

## Development

### Running with Auto-reload

The server automatically reloads when code changes (useful during development):

```bash
python -m entrypoints.http_server
```

### Running in Production Mode

For production, use Gunicorn with Uvicorn workers:

```bash
gunicorn entrypoints.http_server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300 \
  --access-logfile - \
  --error-logfile -
```

### Running in Docker

```bash
# Build
docker build -t pdf-autofiller-mapper -f deployment/docker/Dockerfile .

# Run
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e HTTP_PORT=8000 \
  pdf-autofiller-mapper
```

---

## Error Handling

All endpoints return consistent error responses:

```json
{
  "status": "error",
  "operation": "make_embed_file",
  "error": "Error message here"
}
```

HTTP Status Codes:
- `200` - Success
- `400` - Bad Request (validation error)
- `404` - Not Found (file not found)
- `500` - Internal Server Error

---

## Performance

**Timeouts:**
- Health check: instant
- Extract: ~5-10 seconds
- Map: ~30-45 seconds (cache miss), ~5 seconds (cache hit)
- Embed: ~5-10 seconds
- Full pipeline: ~60-90 seconds (cache miss), ~20 seconds (cache hit)

**Caching:**
- PDF structure cache reduces repeated processing time by ~75%
- RAG predictions cache reduces API calls
- Cache is shared across all entrypoints (CLI, HTTP, Lambda)

---

## Testing

### Manual Testing
```bash
# Start server
python -m entrypoints.http_server

# In another terminal, run tests
python test_http_api.py
```

### Automated Testing
```bash
pytest tests/test_http_server.py
```

---

## Next Steps

1. **Add Authentication** - Implement API key or JWT authentication
2. **Add Rate Limiting** - Prevent abuse with rate limiting
3. **Add Async Job Queue** - For long-running operations
4. **Add Webhooks** - Notify clients when operations complete
5. **Add File Upload** - Allow uploading PDFs via HTTP
6. **Add Batch Operations** - Process multiple PDFs in one request

---

## Troubleshooting

### Server won't start
```bash
# Check if port is already in use
lsof -i :8000

# Use a different port
HTTP_PORT=8080 python -m entrypoints.http_server
```

### Connection refused
- Make sure the server is running
- Check firewall settings
- Verify the host/port configuration

### Input files not found
- Verify files exist in the input directory
- Check file naming pattern matches config.ini
- Verify user_id, session_id, pdf_doc_id are correct

---

## Architecture

```
HTTP Request
     ↓
FastAPI Router
     ↓
entrypoint_helpers.py (shared utilities)
     ↓
operations.py (source-agnostic orchestrator)
     ↓
Storage Handlers (input/output)
     ↓
HTTP Response
```

The HTTP server shares the same core logic as the CLI entrypoint, ensuring consistent behavior across deployment modes.
