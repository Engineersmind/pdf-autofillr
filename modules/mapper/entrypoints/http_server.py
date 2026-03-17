"""
HTTP Server entrypoint for PDF Autofiller Mapper module.

This module provides REST API endpoints for the PDF autofiller mapper,
allowing it to be called via HTTP requests instead of CLI.

Endpoints:
    POST /extract - Extract text from PDF
    POST /map - Map fields
    POST /embed - Embed form fields
    POST /fill - Fill PDF
    POST /make-embed-file - Full pipeline (extract + map + embed)
    GET /health - Health check
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from src.core.logger import logger
from src.core.config import settings
from src.configs.file_config import get_file_config
from src.handlers import operations
from src.utils.entrypoint_helpers import (
    create_job_context,
    cleanup_processing_directory,
    extract_event_params,
)


# ========================================
# Request/Response Models
# ========================================

class OperationRequest(BaseModel):
    """Base request model for all operations."""
    user_id: int = Field(..., description="User ID", example=553)
    session_id: str = Field(..., description="Session ID (UUID)", example="086d6670-81e5-47f4-aecb-e4f7c3ba2a83")
    pdf_doc_id: int = Field(..., description="PDF document ID", example=990)
    investor_type: str = Field(default="individual", description="Investor type", example="individual")
    use_second_mapper: bool = Field(default=False, description="Enable RAG mapper (dual mapper mode)")


class MakeEmbedFileRequest(OperationRequest):
    """Request model for make_embed_file operation."""
    pass


class ExtractRequest(OperationRequest):
    """Request model for extract operation."""
    pass


class MapRequest(OperationRequest):
    """Request model for map operation."""
    pass


class EmbedRequest(OperationRequest):
    """Request model for embed operation."""
    pass


class FillRequest(OperationRequest):
    """Request model for fill operation."""
    data: Dict[str, Any] = Field(..., description="Data to fill in the PDF")


class OperationResponse(BaseModel):
    """Response model for all operations."""
    status: str = Field(..., description="Operation status", example="success")
    operation: str = Field(..., description="Operation name", example="make_embed_file")
    output_paths: Optional[Dict[str, str]] = Field(None, description="Output file paths")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Processing metadata")
    error: Optional[str] = Field(None, description="Error message if status is error")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status", example="healthy")
    version: str = Field(..., description="API version", example="1.0.0")
    storage_type: str = Field(..., description="Storage type", example="local")


# ========================================
# FastAPI App Setup
# ========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events for FastAPI app.
    """
    # Startup
    load_dotenv()
    logger.info("=" * 80)
    logger.info("PDF AUTOFILLER HTTP SERVER STARTING")
    logger.info("=" * 80)
    logger.info(f"Storage type: {os.getenv('STORAGE_TYPE', 'local')}")
    logger.info(f"Data directory: {os.getenv('DATA_DIR', '/app/data')}")
    logger.info(f"Processing directory: {os.getenv('PROCESSING_DIR', '/tmp/processing')}")
    
    yield
    
    # Shutdown
    logger.info("PDF AUTOFILLER HTTP SERVER SHUTTING DOWN")


app = FastAPI(
    title="PDF Autofiller Mapper API",
    description="REST API for PDF field mapping and autofilling",
    version="1.0.0",
    lifespan=lifespan
)


# ========================================
# Helper Functions
# ========================================

async def process_operation(
    operation: str,
    request_data: OperationRequest,
    extra_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Process an operation request using JobContext (UUID-isolated, source-agnostic)."""
    file_config = get_file_config()
    ctx = create_job_context(
        file_config,
        request_data.user_id,
        request_data.session_id,
        request_data.pdf_doc_id,
    )

    logger.info(
        f"HTTP API: op={operation} user={request_data.user_id} "
        f"pdf={request_data.pdf_doc_id} storage={ctx.source_type}"
    )

    # Validate source inputs
    missing = [p for p in (ctx.source_input_pdf, ctx.source_input_json)
               if not ctx.file_exists(p)]
    if missing:
        raise FileNotFoundError(f"Required input files not found: {missing}")

    # Download inputs to isolated temp dir
    import os
    os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
    ctx.download_file(ctx.source_input_pdf,  ctx.local_input_pdf)
    ctx.download_file(ctx.source_input_json, ctx.local_input_json)

    mapping_config = {
        "llm_model":            file_config.get('mapping', 'llm_model',            fallback='gpt-4o'),
        "llm_temperature":      float(file_config.get('mapping', 'llm_temperature', fallback='0.05')),
        "llm_max_tokens":       int(file_config.get('mapping',   'llm_max_tokens',  fallback='8192')),
        "confidence_threshold": float(file_config.get('mapping', 'confidence_threshold', fallback='0.7')),
        "chunking_strategy":    file_config.get('mapping', 'chunking_strategy',    fallback='page'),
    }

    try:
        if operation == "make_embed_file":
            result = await operations.handle_make_embed_file_operation(
                config=ctx,
                user_id=request_data.user_id,
                pdf_doc_id=request_data.pdf_doc_id,
                session_id=request_data.session_id,
                investor_type=request_data.investor_type,
                mapping_config=mapping_config,
                use_second_mapper=request_data.use_second_mapper,
            )
        elif operation == "extract":
            result = await operations.handle_extract_operation(
                config=ctx,
                user_id=request_data.user_id,
                pdf_doc_id=request_data.pdf_doc_id,
                session_id=request_data.session_id,
            )
        elif operation == "map":
            result = await operations.handle_map_operation(
                config=ctx,
                mapping_config=mapping_config,
                user_id=request_data.user_id,
                pdf_doc_id=request_data.pdf_doc_id,
                session_id=request_data.session_id,
                investor_type=request_data.investor_type,
            )
        elif operation == "embed":
            result = await operations.handle_embed_operation(
                config=ctx,
                user_id=request_data.user_id,
                pdf_doc_id=request_data.pdf_doc_id,
                session_id=request_data.session_id,
            )
        elif operation == "fill":
            result = await operations.handle_fill_operation(
                config=ctx,
                user_id=request_data.user_id,
                pdf_doc_id=request_data.pdf_doc_id,
                session_id=request_data.session_id,
                data=(extra_params or {}).get("data", {}),
            )
        else:
            raise ValueError(f"Unknown operation: {operation!r}")
    finally:
        cleanup_processing_directory(ctx.processing_dir)

    return {
        "status":       "success",
        "operation":    operation,
        "output_paths": {k: v for k, v in result.get('outputs', {}).items() if v},
        "metadata":     result,
    }


# ========================================
# API Endpoints
# ========================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status and version info
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "storage_type": settings.storage_type
    }


@app.post("/make-embed-file", response_model=OperationResponse)
async def make_embed_file(request: MakeEmbedFileRequest):
    """
    Run full pipeline: Extract + Map + Embed.
    
    This endpoint processes a PDF through the complete pipeline:
    1. Extract text and form fields
    2. Map fields to investor data schema
    3. Embed mappings into PDF form fields
    
    Args:
        request: Make embed file request
        
    Returns:
        Operation result with output file paths
        
    Example:
        ```
        POST /make-embed-file
        {
            "user_id": 553,
            "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
            "pdf_doc_id": 990,
            "investor_type": "individual",
            "use_second_mapper": true
        }
        ```
    """
    result = await process_operation("make_embed_file", request)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@app.post("/extract", response_model=OperationResponse)
async def extract(request: ExtractRequest):
    """
    Extract text and form fields from PDF.
    
    Args:
        request: Extract request
        
    Returns:
        Extraction result with output file path
    """
    result = await process_operation("extract", request)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@app.post("/map", response_model=OperationResponse)
async def map_fields(request: MapRequest):
    """
    Map extracted fields to investor data schema.
    
    Args:
        request: Map request
        
    Returns:
        Mapping result with output file path
    """
    result = await process_operation("map", request)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@app.post("/embed", response_model=OperationResponse)
async def embed(request: EmbedRequest):
    """
    Embed field mappings into PDF form fields.
    
    Args:
        request: Embed request
        
    Returns:
        Embed result with output file path
    """
    result = await process_operation("embed", request)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


@app.post("/fill", response_model=OperationResponse)
async def fill(request: FillRequest):
    """
    Fill PDF with provided data.
    
    Args:
        request: Fill request with data
        
    Returns:
        Fill result with output file path
    """
    result = await process_operation("fill", request, extra_params={"data": request.data})
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return result


# ========================================
# Main entry point
# ========================================

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.getenv("HTTP_PORT", "8000"))
    host = os.getenv("HTTP_HOST", "0.0.0.0")
    
    logger.info(f"Starting HTTP server on {host}:{port}")
    
    uvicorn.run(
        "entrypoints.http_server:app",
        host=host,
        port=port,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
