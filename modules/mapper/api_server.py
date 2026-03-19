"""
FastAPI Server for PDF Autofiller Mapper Module

Run with: uvicorn api_server:app --reload --port 8000

This provides HTTP API endpoints for the mapper module operations.
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
import os
import tempfile
from pathlib import Path

# Import mapper operations
from src.handlers.operations import (
    handle_extract_operation,
    handle_map_operation,
    handle_embed_operation,
    handle_fill_operation,
    handle_make_embed_file_operation,
    handle_check_embed_file_operation,
    handle_fill_pdf_operation,
    handle_run_all_operation
)
from src.core.logger import logger

app = FastAPI(
    title="PDF Autofiller Mapper API",
    description="API for PDF form field extraction, mapping, embedding, and filling",
    version="1.0.0"
)


# ============================================================================
# Request Models
# ============================================================================

class ExtractRequest(BaseModel):
    pdf_path: str = Field(..., description="Path to PDF file (local)")
    user_id: Optional[int] = Field(1, description="User ID")
    session_id: Optional[int] = Field(None, description="Session ID")
    pdf_doc_id: Optional[int] = Field(100, description="PDF document ID")


class MapRequest(BaseModel):
    extracted_json_path: str = Field(..., description="Path to extracted JSON")
    input_json_path: str = Field(..., description="Path to input JSON with data")
    user_id: Optional[int] = Field(1, description="User ID")
    session_id: Optional[int] = Field(None, description="Session ID")
    pdf_doc_id: Optional[int] = Field(100, description="PDF document ID")
    investor_type: Optional[str] = Field("individual", description="Investor type")


class EmbedRequest(BaseModel):
    original_pdf_path: str = Field(..., description="Path to original PDF")
    extracted_json_path: str = Field(..., description="Path to extracted JSON")
    mapping_json_path: str = Field(..., description="Path to mapping JSON")
    radio_groups_path: str = Field(..., description="Path to radio groups JSON")
    user_id: Optional[int] = Field(1, description="User ID")
    session_id: Optional[int] = Field(None, description="Session ID")
    pdf_doc_id: Optional[int] = Field(100, description="PDF document ID")


class FillRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    pdf_doc_id: str = Field(..., description="PDF document ID")


class MakeEmbedRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    pdf_doc_id: str = Field(..., description="PDF document ID")
    investor_type: Optional[str] = Field("individual", description="Investor type")
    use_second_mapper: Optional[bool] = Field(False, description="Use dual mapper with RAG")


class FillPDFRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    pdf_doc_id: str = Field(..., description="PDF document ID")


class CheckEmbedRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    pdf_doc_id: str = Field(..., description="PDF document ID")


class RunAllRequest(BaseModel):
    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    pdf_doc_id: str = Field(..., description="PDF document ID")
    investor_type: Optional[str] = Field("individual", description="Investor type")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "PDF Autofiller Mapper API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "upload": "/upload/{user_id}/{session_id}/{pdf_doc_id}/{filename}",
            "make_embed_file": "/mapper/make-embed-file",
            "fill": "/mapper/fill",
            "download": "/download?path=<file_path_or_cloud_uri>",
            "check_embed": "/mapper/check-embed-file",
            "fill_pdf": "/mapper/fill-pdf",
            "run_all": "/mapper/run-all",
            "extract": "/mapper/extract",
            "map": "/mapper/map",
            "embed": "/mapper/embed",
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


# ── Upload ────────────────────────────────────────────────────────────────────

_ALLOWED_FILENAMES = {
    "input.pdf",
    "global_schema.json",
    "input_data.json",
}

@app.post("/upload/{user_id}/{session_id}/{pdf_doc_id}/{filename}")
async def upload_input_file(
    user_id: str,
    session_id: str,
    pdf_doc_id: str,
    filename: str,
    file: UploadFile = File(...),
):
    """
    Upload an input file for a specific job.

    Places the file at:
        {MAPPER_INPUT_PATH}/{user_id}/{session_id}/{pdf_doc_id}/{filename}

    Accepted filenames:
        - input.pdf            — PDF template
        - global_schema.json   — Keys-only schema for make_embed_file
        - input_data.json      — Per-user fill data for fill

    Example:
        curl -X POST \\
          "http://localhost:8000/upload/1/1/100/input.pdf" \\
          -F "file=@/local/path/form.pdf"
    """
    if filename not in _ALLOWED_FILENAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Filename '{filename}' is not allowed. Must be one of: {sorted(_ALLOWED_FILENAMES)}",
        )

    from src.storage.storage_config import get_storage_config
    sc = get_storage_config()
    dest_path = sc.input_path(user_id, session_id, pdf_doc_id, filename)

    contents = await file.read()

    if dest_path.startswith(("s3://", "azure://", "gs://")):
        # Cloud backend — write to a temp file then upload via the storage backend
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        try:
            sc.backend.upload_file(tmp_path, dest_path)
        finally:
            os.unlink(tmp_path)
    else:
        # Local backend — write directly to the configured input path
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(contents)

    logger.info(f"Uploaded {filename} for user={user_id} session={session_id} pdf={pdf_doc_id} → {dest_path}")
    return JSONResponse(content={
        "status": "success",
        "path": dest_path,
        "user_id": user_id,
        "session_id": session_id,
        "pdf_doc_id": pdf_doc_id,
        "filename": filename,
        "size_bytes": len(contents),
    })


@app.post("/mapper/extract")
async def extract(request: ExtractRequest):
    """
    Extract fields from PDF
    
    Extracts form fields, headers, and structure from the PDF.
    """
    try:
        logger.info(f"API: Extract request for {request.pdf_path}")
        
        result = await handle_extract_operation(
            input_file=request.pdf_path,
            user_id=request.user_id,
            session_id=request.session_id,
            pdf_doc_id=request.pdf_doc_id
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Extract failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mapper/map")
async def map_fields(request: MapRequest):
    """
    Map fields to target schema
    
    Maps extracted fields to input JSON keys using semantic mapper.
    """
    try:
        logger.info(f"API: Map request for {request.extracted_json_path}")
        
        # Load mapping config from config.ini
        from src.core.config import get_mapper_config
        mapping_config = get_mapper_config()
        
        result = await handle_map_operation(
            extracted_json_path=request.extracted_json_path,
            input_json_path=request.input_json_path,
            mapping_config=mapping_config,
            user_id=request.user_id,
            session_id=request.session_id,
            pdf_doc_id=request.pdf_doc_id,
            investor_type=request.investor_type
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Map failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mapper/embed")
async def embed(request: EmbedRequest):
    """
    Embed metadata into PDF
    
    Embeds field mappings into the PDF for later filling.
    """
    try:
        logger.info(f"API: Embed request for {request.original_pdf_path}")
        
        result = await handle_embed_operation(
            original_pdf_path=request.original_pdf_path,
            extracted_json_path=request.extracted_json_path,
            mapping_json_path=request.mapping_json_path,
            radio_groups_path=request.radio_groups_path,
            user_id=request.user_id,
            session_id=request.session_id,
            pdf_doc_id=request.pdf_doc_id
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Embed failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mapper/fill")
async def fill(request: FillRequest):
    """
    Fill PDF with data

    Derives all file paths from (user_id, session_id, pdf_doc_id) using config.ini.
    The embedded PDF must have been produced by /mapper/make-embed-file first,
    and the per-user input_data.json must be at the configured input path.
    """
    try:
        logger.info(f"API: Fill request user={request.user_id} session={request.session_id} pdf={request.pdf_doc_id}")

        from src.storage.storage_config import get_storage_config
        from src.utils.entrypoint_helpers import create_job_context
        config = create_job_context(get_storage_config(), request.user_id, request.session_id, request.pdf_doc_id)

        # ── Pre-flight checks ────────────────────────────────────────────────
        missing = []
        if not os.path.isfile(config.dest_embedded_pdf):
            missing.append(f"embedded_pdf not found: {config.dest_embedded_pdf}")
        if not os.path.isfile(config.source_input_json):
            missing.append(f"input_json not found: {config.source_input_json}")
        if missing:
            raise HTTPException(status_code=400, detail={"missing_files": missing})

        # Use the config-derived paths (no caller-supplied paths needed)
        config.local_embedded_pdf = config.dest_embedded_pdf
        config.s3_embedded_pdf    = config.dest_embedded_pdf

        result = await handle_fill_operation(
            config=config,
            user_id=request.user_id,
            session_id=request.session_id,
            pdf_doc_id=request.pdf_doc_id
        )

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fill failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mapper/make-embed-file")
async def make_embed_file(request: MakeEmbedRequest):
    """
    Make embed file (Extract → Map → Embed pipeline)

    Derives all file paths from (user_id, session_id, pdf_doc_id) using MAPPER_* env vars.
    Required input files must be pre-placed at their configured input paths:
      - input PDF:      {MAPPER_INPUT_PATH}/{user_id}/{session_id}/{pdf_doc_id}/input.pdf
      - global schema:  {MAPPER_INPUT_PATH}/{user_id}/{session_id}/{pdf_doc_id}/global_schema.json
    """
    try:
        logger.info(f"API: Make embed file user={request.user_id} session={request.session_id} pdf={request.pdf_doc_id}")

        from src.storage.storage_config import get_storage_config
        from src.utils.entrypoint_helpers import create_job_context
        sc = get_storage_config()
        config = create_job_context(sc, request.user_id, request.session_id, request.pdf_doc_id)

        # ── Pre-flight checks (paths derived from config + IDs) ──────────────
        missing = []
        if not os.path.isfile(config.source_input_pdf):
            missing.append(f"input_pdf not found: {config.source_input_pdf}")
        if not os.path.isfile(config.source_global_json):
            missing.append(f"global_json not found: {config.source_global_json}")
        if missing:
            raise HTTPException(status_code=400, detail={"missing_files": missing})

        from src.core.config import get_mapper_config
        mapping_config = get_mapper_config()

        result = await handle_make_embed_file_operation(
            config=config,
            user_id=request.user_id,
            pdf_doc_id=request.pdf_doc_id,
            session_id=request.session_id,
            investor_type=request.investor_type,
            mapping_config=mapping_config,
            use_second_mapper=request.use_second_mapper
        )

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Make embed file failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mapper/fill-pdf")
async def fill_pdf(request: FillPDFRequest):
    """
    Fill PDF (alias for /mapper/fill with safety checks).
    Derives all paths from (user_id, session_id, pdf_doc_id) via config.ini.
    """
    try:
        logger.info(f"API: Fill PDF user={request.user_id} session={request.session_id} pdf={request.pdf_doc_id}")

        from src.storage.storage_config import get_storage_config
        from src.utils.entrypoint_helpers import create_job_context
        config = create_job_context(get_storage_config(), request.user_id, request.session_id, request.pdf_doc_id)
        config.local_embedded_pdf = config.dest_embedded_pdf
        config.s3_embedded_pdf    = config.dest_embedded_pdf

        result = await handle_fill_pdf_operation(
            config=config,
            user_id=request.user_id,
            session_id=request.session_id,
            pdf_doc_id=request.pdf_doc_id
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Fill PDF failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mapper/check-embed-file")
async def check_embed_file(request: CheckEmbedRequest):
    """
    Check if the embedded PDF for this job exists and is ready for filling.
    """
    try:
        logger.info(f"API: Check embed file user={request.user_id} session={request.session_id} pdf={request.pdf_doc_id}")

        from src.storage.storage_config import get_storage_config
        from src.utils.entrypoint_helpers import create_job_context
        config = create_job_context(get_storage_config(), request.user_id, request.session_id, request.pdf_doc_id)

        result = await handle_check_embed_file_operation(
            config=config,
            user_id=request.user_id,
            session_id=request.session_id
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Check embed file failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mapper/run-all")
async def run_all(request: RunAllRequest):
    """
    Run complete pipeline (Extract → Map → Embed → Fill)

    Derives all file paths from (user_id, session_id, pdf_doc_id) using MAPPER_* env vars.
    All three input files must be pre-placed at their configured input paths.
    """
    try:
        logger.info(f"API: Run all user={request.user_id} session={request.session_id} pdf={request.pdf_doc_id}")

        from src.storage.storage_config import get_storage_config
        from src.utils.entrypoint_helpers import create_job_context
        config = create_job_context(get_storage_config(), request.user_id, request.session_id, request.pdf_doc_id)

        # ── Pre-flight checks ────────────────────────────────────────────────
        missing = []
        if not os.path.isfile(config.source_input_pdf):
            missing.append(f"input_pdf not found: {config.source_input_pdf}")
        if not os.path.isfile(config.source_global_json):
            missing.append(f"global_json not found: {config.source_global_json}")
        if not os.path.isfile(config.source_input_json):
            missing.append(f"input_json not found: {config.source_input_json}")
        if missing:
            raise HTTPException(status_code=400, detail={"missing_files": missing})

        from src.core.config import get_mapper_config
        mapping_config = get_mapper_config()

        result = await handle_run_all_operation(
            input_pdf=config.source_input_pdf,
            global_json=config.source_global_json,
            input_json=config.source_input_json,
            mapping_config=mapping_config,
            user_id=request.user_id,
            session_id=request.session_id,
            pdf_doc_id=request.pdf_doc_id
        )

        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Run all failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download")
async def download_file(
    path: str = Query(..., description="Full path to the file (local path or cloud URI such as s3://, azure://, gs://)"),
):
    """
    Download a file from any configured storage backend.

    Works for local filesystem paths and cloud storage URIs alike.
    The path is the value returned in ``output_paths`` by any processing endpoint.

    Args:
        path: Full file path or cloud URI
            - Local:  /app/data/output/1/1/100/filled.pdf
            - S3:     s3://my-bucket/prefix/output/1/1/100/filled.pdf
            - Azure:  azure://my-container/prefix/output/1/1/100/filled.pdf
            - GCS:    gs://my-bucket/prefix/output/1/1/100/filled.pdf

    Returns:
        File content as ``application/octet-stream`` download.

    Example:
        GET /download?path=/app/data/output/1/1/100/filled.pdf
        GET /download?path=s3://bucket/prefix/output/1/1/100/filled.pdf
    """
    try:
        logger.info(f"API: Download request for {path}")

        from src.storage.storage_config import get_storage_config
        sc = get_storage_config()
        filename = Path(path.rstrip("/")).name

        if path.startswith(("s3://", "azure://", "gs://")):
            # Cloud storage — download to a temp file and stream it back
            if not sc.backend.file_exists(path):
                raise HTTPException(status_code=404, detail=f"File not found: {path}")

            suffix = Path(filename).suffix or ".bin"
            tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            os.close(tmp_fd)
            try:
                sc.backend.download_file(path, tmp_path)
                # Stream the file and delete temp after sending
                def _iter_file():
                    with open(tmp_path, "rb") as fh:
                        yield from iter(lambda: fh.read(65536), b"")
                    os.unlink(tmp_path)

                return StreamingResponse(
                    _iter_file(),
                    media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )
            except HTTPException:
                os.unlink(tmp_path)
                raise
            except Exception:
                os.unlink(tmp_path)
                raise

        else:
            # Local storage — validate and serve directly
            resolved = Path(path)
            if not resolved.is_absolute():
                resolved = Path.cwd() / resolved
            resolved = resolved.resolve()

            if not resolved.exists():
                raise HTTPException(status_code=404, detail=f"File not found: {path}")
            if not resolved.is_file():
                raise HTTPException(status_code=400, detail=f"Not a file: {path}")

            logger.info(f"Serving local file: {resolved}")
            return FileResponse(
                path=str(resolved),
                filename=filename,
                media_type="application/octet-stream",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc)
        }
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting PDF Autofiller Mapper API Server...")
    logger.info("API will be available at: http://localhost:8000")
    logger.info("API docs at: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
