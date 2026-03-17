"""
Azure Functions entrypoint for PDF Mapper Module.

This is a THIN wrapper that:
1. Parses Azure Functions HTTP trigger events
2. Validates authentication (X-API-Key header)
3. Builds a UUID-scoped JobContext via create_job_context()
4. Downloads inputs, runs the operation, cleans up in try/finally
5. Returns Azure Functions HTTP response format

The actual business logic is in src/handlers/operations.py
"""

import json
import logging
import asyncio
import os
from typing import Any, Dict, Optional

# Azure Functions imports
try:
    import azure.functions as func
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    func = None

from src.core.logger import setup_logging
from src.core.config import settings
from src.configs.file_config import get_file_config
from src.utils.entrypoint_helpers import create_job_context, cleanup_processing_directory
from src.handlers import operations

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────

def _check_auth(req: "func.HttpRequest") -> Optional["func.HttpResponse"]:
    """Return an error response if the API key is wrong, else None."""
    expected = getattr(settings, 'mapper_lambda_api_token', None) or os.getenv('MAPPER_API_TOKEN')
    if not expected:
        return None  # auth not configured → open

    key = req.headers.get('x-api-key') or req.headers.get('X-API-Key')
    if not key:
        return func.HttpResponse(
            json.dumps({'error': 'Unauthorized', 'message': 'Missing X-API-Key header'}),
            status_code=401, mimetype='application/json'
        )
    if key != expected:
        return func.HttpResponse(
            json.dumps({'error': 'Forbidden', 'message': 'Invalid API key'}),
            status_code=403, mimetype='application/json'
        )
    return None


# ─────────────────────────────────────────────────────────────
# Mapping config helper
# ─────────────────────────────────────────────────────────────

def _mapping_config(file_config) -> dict:
    return {
        'llm_model':            file_config.get('mapping', 'llm_model',            fallback='gpt-4o'),
        'llm_temperature':      float(file_config.get('mapping', 'llm_temperature', fallback='0.05')),
        'llm_max_tokens':       int(file_config.get('mapping',   'llm_max_tokens',  fallback='8192')),
        'confidence_threshold': float(file_config.get('mapping', 'confidence_threshold', fallback='0.7')),
        'chunking_strategy':    file_config.get('mapping', 'chunking_strategy',    fallback='page'),
    }


# ─────────────────────────────────────────────────────────────
# Operation router
# ─────────────────────────────────────────────────────────────

async def route_operation(event: dict) -> dict:
    """
    Build JobContext, download inputs, run the requested operation, clean up.

    All operations require: user_id, session_id, pdf_doc_id.
    Input blob paths are resolved from config.ini + those IDs.
    For operations that need a specific source blob (fill_pdf, check_embed_file),
    pass input_pdf / embedded_pdf explicitly in the payload.
    """
    operation  = event.get('operation')
    user_id    = event.get('user_id')
    session_id = event.get('session_id', '')
    pdf_doc_id = event.get('pdf_doc_id')

    if not operation:
        raise ValueError("Missing required parameter: operation")
    if user_id is None:
        raise ValueError("Missing required parameter: user_id")
    if pdf_doc_id is None:
        raise ValueError("Missing required parameter: pdf_doc_id")

    file_config = get_file_config()
    ctx = create_job_context(file_config, user_id, session_id, pdf_doc_id)
    mapping_cfg = _mapping_config(file_config)

    logger.info(f"Azure op={operation} user={user_id} pdf={pdf_doc_id} storage={ctx.source_type}")

    try:
        if operation == 'make_embed_file':
            os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
            ctx.download_file(ctx.source_input_pdf,  ctx.local_input_pdf)
            ctx.download_file(ctx.source_input_json, ctx.local_input_json)
            return await operations.handle_make_embed_file_operation(
                config=ctx,
                user_id=user_id,
                pdf_doc_id=pdf_doc_id,
                session_id=session_id,
                investor_type=event.get('investor_type', 'individual'),
                mapping_config=mapping_cfg,
                use_second_mapper=event.get('use_second_mapper', False),
            )

        elif operation == 'extract':
            os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
            ctx.download_file(ctx.source_input_pdf, ctx.local_input_pdf)
            return await operations.handle_extract_operation(
                config=ctx,
                user_id=user_id,
                pdf_doc_id=pdf_doc_id,
                session_id=session_id,
            )

        elif operation == 'map':
            os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
            ctx.download_file(ctx.source_input_pdf,  ctx.local_input_pdf)
            ctx.download_file(ctx.source_input_json, ctx.local_input_json)
            return await operations.handle_map_operation(
                config=ctx,
                mapping_config=mapping_cfg,
                user_id=user_id,
                pdf_doc_id=pdf_doc_id,
                session_id=session_id,
                investor_type=event.get('investor_type', 'individual'),
            )

        elif operation == 'embed':
            os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
            ctx.download_file(ctx.source_input_pdf, ctx.local_input_pdf)
            return await operations.handle_embed_operation(
                config=ctx,
                user_id=user_id,
                pdf_doc_id=pdf_doc_id,
                session_id=session_id,
            )

        elif operation == 'fill':
            os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
            ctx.download_file(ctx.source_input_pdf,  ctx.local_input_pdf)
            ctx.download_file(ctx.source_input_json, ctx.local_input_json)
            return await operations.handle_fill_operation(
                config=ctx,
                user_id=user_id,
                pdf_doc_id=pdf_doc_id,
                session_id=session_id,
            )

        elif operation == 'run_all':
            input_pdf  = event.get('input_pdf')
            input_json = event.get('input_json')
            if not input_pdf:
                raise ValueError("Missing required parameter: input_pdf")
            if not input_json:
                raise ValueError("Missing required parameter: input_json")
            ctx.source_input_pdf  = input_pdf
            ctx.source_input_json = input_json
            os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
            ctx.download_file(input_pdf,  ctx.local_input_pdf)
            ctx.download_file(input_json, ctx.local_input_json)
            return await operations.handle_run_all_operation(
                config=ctx,
                mapping_config=mapping_cfg,
                user_id=user_id,
                pdf_doc_id=pdf_doc_id,
                session_id=session_id,
            )

        elif operation == 'fill_pdf':
            embedded_pdf = event.get('embedded_pdf')
            input_json   = event.get('input_json')
            if not embedded_pdf:
                raise ValueError("Missing required parameter: embedded_pdf")
            if not input_json:
                raise ValueError("Missing required parameter: input_json")
            ctx.s3_embedded_pdf = embedded_pdf
            os.makedirs(os.path.dirname(ctx.local_embedded_pdf), exist_ok=True)
            ctx.download_file(embedded_pdf, ctx.local_embedded_pdf)
            ctx.download_file(input_json,   ctx.local_input_json)
            return await operations.handle_fill_pdf_operation(
                config=ctx,
                user_id=user_id,
                session_id=session_id,
                pdf_doc_id=pdf_doc_id,
                input_json_doc_id=event.get('input_json_doc_id'),
            )

        elif operation == 'check_embed_file':
            embedded_pdf = event.get('embedded_pdf', ctx.dest_embedded_pdf)
            os.makedirs(os.path.dirname(ctx.local_embedded_pdf), exist_ok=True)
            try:
                ctx.download_file(embedded_pdf, ctx.local_embedded_pdf)
            except Exception as e:
                logger.info(f"Embedded PDF not yet in storage (expected on first check): {e}")
            return await operations.handle_check_embed_file_operation(
                config=ctx,
                user_id=user_id,
                session_id=session_id,
            )

        elif operation == 'make_form_fields_data_points':
            os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
            ctx.download_file(ctx.source_input_pdf, ctx.local_input_pdf)
            return await operations.handle_make_form_fields_data_points(
                config=ctx,
                user_id=user_id,
                session_id=session_id,
                pdf_doc_id=pdf_doc_id,
            )

        elif operation == 'refresh':
            input_pdf = event.get('input_pdf')
            if not input_pdf:
                raise ValueError("Missing required parameter: input_pdf")
            return await operations.handle_refresh_operation(
                input_pdf=input_pdf,
                user_id=user_id,
                session_id=session_id,
            )

        else:
            raise ValueError(f"Unknown operation: {operation!r}")

    finally:
        cleanup_processing_directory(ctx.processing_dir)


# ─────────────────────────────────────────────────────────────
# Azure Functions entry point
# ─────────────────────────────────────────────────────────────

async def main(req: "func.HttpRequest") -> "func.HttpResponse":
    """Azure Functions HTTP trigger entry point (async)."""
    if not AZURE_AVAILABLE:
        return func.HttpResponse(
            json.dumps({'error': 'azure-functions package not installed'}),
            status_code=500, mimetype='application/json'
        )

    logger.info("Azure Function triggered")

    # Auth
    auth_err = _check_auth(req)
    if auth_err:
        return auth_err

    try:
        try:
            event = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({'error': 'Invalid JSON in request body'}),
                status_code=400, mimetype='application/json'
            )

        result = await route_operation(event)

        return func.HttpResponse(
            json.dumps({'message': 'Processing completed successfully', 'result': result}, indent=2),
            status_code=200, mimetype='application/json'
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        return func.HttpResponse(
            json.dumps({'error': 'Validation Error', 'message': str(e)}),
            status_code=400, mimetype='application/json'
        )

    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({'error': str(e), 'message': 'Processing failed'}),
            status_code=500, mimetype='application/json'
        )
