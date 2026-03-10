# Implementation Checklist

## Design Phase ✅ COMPLETE

- [x] Confirm architecture approach (source-agnostic operations)
- [x] Design event format (same for all sources)
- [x] Design file lifecycle (copy in → process → copy out → cleanup)
- [x] Design path patterns (config.ini with variables)
- [x] Design three storage layers (source, processing, output)
- [x] Confirm ephemeral storage (like Lambda)

## Implementation Phase ✅ COMPLETE

### Core Files

- [x] **config.ini** - Updated with:
  - [x] `[local]` section with paths
  - [x] `[file_naming]` section with patterns
  - [x] File naming patterns with `{user_id}`, `{session_id}`, `{pdf_doc_id}`

- [x] **src/configs/file_config.py** - Created with:
  - [x] Config loader (`FileConfig` class)
  - [x] Path builder (`build_file_path()`)
  - [x] Source input paths (`get_source_input_path()`)
  - [x] Source output paths (`get_source_output_path()`)
  - [x] Processing paths (`get_all_processing_paths()`)

- [x] **entrypoints/local.py** - Created with:
  - [x] Main handler (`handle_local_event()`)
  - [x] Path builder (`_build_file_paths()`)
  - [x] Input preparation (`_prepare_input_files()`)
  - [x] Config creation (`_create_storage_config()`)
  - [x] Operation caller (`_call_operation()`)
  - [x] Result saver (`_save_results()`)
  - [x] Cleanup (`_cleanup_temp_files()`)

### Documentation

- [x] **DESIGN_LOCAL_DEPLOYMENT.md** - Complete architecture doc
- [x] **IMPLEMENTATION_SUMMARY.md** - Implementation summary
- [x] **ARCHITECTURE_DIAGRAMS.md** - Visual diagrams

### Testing

- [x] **test_local_entrypoint.py** - Test script created

## Testing Phase ⏳ NEXT

### Unit Tests

- [ ] Test `file_config.py`:
  - [ ] Test config loading
  - [ ] Test path building with variables
  - [ ] Test source input paths
  - [ ] Test source output paths
  - [ ] Test processing paths

- [ ] Test `entrypoints/local.py`:
  - [ ] Test path building
  - [ ] Test file preparation (copy in)
  - [ ] Test result saving (copy out)
  - [ ] Test cleanup

### Integration Tests

- [ ] Create test directories:
  ```bash
  mkdir -p /app/data/input
  mkdir -p /app/data/output
  mkdir -p /tmp/processing
  ```

- [ ] Put test files:
  ```bash
  cp test.pdf /app/data/input/553_086d_990.pdf
  cp test.json /app/data/input/553_086d_990.json
  ```

- [ ] Run test:
  ```bash
  python test_local_entrypoint.py
  ```

- [ ] Verify:
  - [ ] Files copied to /tmp/processing/
  - [ ] Operations executed
  - [ ] Results in /app/data/output/
  - [ ] /tmp/processing/ cleaned up

### End-to-End Tests

- [ ] Test with real PDF:
  - [ ] Small PDF (4 pages)
  - [ ] Medium PDF (20 pages)
  - [ ] Large PDF (100+ pages)

- [ ] Test all operations:
  - [ ] `make_embed_file`
  - [ ] `fill_pdf`
  - [ ] `run_all`

- [ ] Test error handling:
  - [ ] Missing input file
  - [ ] Invalid JSON
  - [ ] Processing failure
  - [ ] Cleanup after error

## API Integration ⏳ TODO

### Update api_server.py

- [ ] Update `/mapper/make-embed-file` endpoint:
  ```python
  from entrypoints.local import handle_local_event
  
  @app.post("/mapper/make-embed-file")
  async def make_embed_file(request):
      event = {
          "operation": "make_embed_file",
          "user_id": request.user_id,
          "session_id": request.session_id,
          "pdf_doc_id": request.pdf_doc_id,
          ...
      }
      result = handle_local_event(event)
      return result
  ```

- [ ] Update other endpoints:
  - [ ] `/mapper/fill-pdf`
  - [ ] `/mapper/run-all`

- [ ] Add upload endpoint (for SDK):
  ```python
  @app.post("/upload")
  async def upload_file(file: UploadFile, ...):
      # Save to /app/data/input/ with correct naming
      pass
  ```

- [ ] Add download endpoint (for SDK):
  ```python
  @app.get("/download/{file_path:path}")
  async def download_file(file_path: str):
      # Serve from /app/data/output/
      pass
  ```

### Test API

- [ ] Test via curl:
  ```bash
  curl -X POST http://localhost:8000/mapper/make-embed-file \
    -H "Content-Type: application/json" \
    -d '{"user_id": 553, "session_id": "xxx", "pdf_doc_id": 990}'
  ```

- [ ] Test via Python SDK
- [ ] Test via Postman

## Docker Integration ⏳ TODO

### Update Dockerfile

- [ ] Ensure directories exist:
  ```dockerfile
  RUN mkdir -p /app/data/input /app/data/output /tmp/processing
  ```

- [ ] Set correct permissions:
  ```dockerfile
  RUN chown -R appuser:appuser /app/data /tmp/processing
  ```

### Update docker-run-local.sh

- [ ] Add volume mounts:
  ```bash
  docker run \
    -v ~/data/input:/app/data/input \
    -v ~/data/output:/app/data/output \
    ...
  ```

### Test Docker

- [ ] Build image:
  ```bash
  ./docker-build.sh
  ```

- [ ] Run container:
  ```bash
  ./docker-run-local.sh
  ```

- [ ] Test API in container
- [ ] Verify volume mounts
- [ ] Verify file operations

## AWS Entrypoint ⏳ FUTURE

### Create entrypoints/aws_lambda_handler.py

- [ ] Follow same pattern as local.py
- [ ] Use boto3 for S3 operations:
  - [ ] `s3_download()` instead of `copy()`
  - [ ] `s3_upload()` instead of `copy()`
- [ ] Same processing logic (call operations)
- [ ] Same cleanup logic

### Test AWS Lambda

- [ ] Test locally with SAM/LocalStack
- [ ] Deploy to AWS Lambda
- [ ] Test with S3 trigger
- [ ] Verify S3 uploads

## Azure Entrypoint ⏳ FUTURE

### Create entrypoints/azure_function.py

- [ ] Follow same pattern as local.py
- [ ] Use azure-storage-blob for Blob operations:
  - [ ] `blob_download()` instead of `copy()`
  - [ ] `blob_upload()` instead of `copy()`
- [ ] Same processing logic (call operations)
- [ ] Same cleanup logic

### Test Azure Functions

- [ ] Test locally with Azure Functions Core Tools
- [ ] Deploy to Azure
- [ ] Test with Blob trigger
- [ ] Verify Blob uploads

## SDK Updates ⏳ FUTURE

### Add Upload/Download to SDK

- [ ] Add `upload_file()` method:
  ```python
  def upload_file(self, local_path, destination):
      # POST /upload with multipart/form-data
      pass
  ```

- [ ] Add `download_file()` method:
  ```python
  def download_file(self, source_path, local_path):
      # GET /download/{source_path}
      pass
  ```

- [ ] Update high-level methods:
  ```python
  def make_embed_file(self, pdf_path, ...):
      # Auto-upload if needed
      # Call API
      # Auto-download if needed
      pass
  ```

### Test SDK

- [ ] Test with volume mounts (same machine)
- [ ] Test with upload/download (different machine)
- [ ] Test error handling

## Documentation Updates ⏳ FUTURE

### Update README

- [ ] Add local deployment section
- [ ] Add Docker usage examples
- [ ] Add SDK usage examples
- [ ] Add troubleshooting

### Update API Docs

- [ ] Document new event format
- [ ] Document path requirements
- [ ] Document config.ini structure

### Create Deployment Guide

- [ ] Local deployment guide
- [ ] AWS deployment guide
- [ ] Azure deployment guide
- [ ] GCP deployment guide

## Other Modules ⏳ FUTURE

### Apply Same Pattern

- [ ] **modules/chatbot/** - Same entrypoint pattern
- [ ] **modules/rag/** - Same entrypoint pattern
- [ ] **modules/orchestrator/** - Same entrypoint pattern

Each module gets:
- [ ] Updated config.ini
- [ ] src/configs/file_config.py
- [ ] entrypoints/local.py
- [ ] entrypoints/aws_lambda.py
- [ ] entrypoints/azure_function.py

---

## Current Status

### ✅ Completed (Design Phase)
- Architecture designed
- Core files implemented
- Documentation complete
- Test script ready

### ⏳ Next Steps (Testing Phase)
1. Run `test_local_entrypoint.py`
2. Fix any issues
3. Test with real PDFs
4. Update `api_server.py`
5. Test via API

### 📋 Backlog (Future)
- AWS Lambda entrypoint
- Azure Functions entrypoint
- SDK upload/download
- Apply to other modules

---

## Success Criteria

### Phase 1: Local Deployment ✅
- [x] Design complete
- [x] Code implemented
- [ ] Tests passing
- [ ] API working
- [ ] Docker working

### Phase 2: AWS Deployment
- [ ] AWS entrypoint created
- [ ] Tests passing
- [ ] Lambda deployed
- [ ] S3 integration working

### Phase 3: Multi-Cloud
- [ ] Azure entrypoint created
- [ ] All sources working
- [ ] SDK updated
- [ ] Documentation complete

---

**Next Action:** Run `python test_local_entrypoint.py` to verify design! 🚀
