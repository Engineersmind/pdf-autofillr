"""
Local / Docker entrypoint.

Flow per request:
  1. Load config.ini + .env
  2. Build JobContext  (PathResolver + StorageBackend — from config.ini source_type)
  3. Download inputs from source → /tmp/processing/
  4. Call operation  (source-agnostic)
  5. Upload outputs from /tmp/processing/ → source
  6. Cleanup /tmp/processing/
  7. Return result

To switch storage backend: change [general] source_type in config.ini.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

from src.configs.file_config import get_file_config
from src.handlers import operations
from src.core.logger import logger
from src.utils.entrypoint_helpers import (
    create_job_context,
    cleanup_processing_directory,
    extract_event_params,
)


async def handle_local_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle a local/Docker deployment event.

    Args:
        event: {
            "operation":         "make_embed_file" | "fill_pdf" | "run_all",
            "user_id":           553,
            "session_id":        "086d6670-...",
            "pdf_doc_id":        990,
            "investor_type":     "individual",   # optional
            "use_second_mapper": True            # optional
        }

    Returns:
        {"status": "success"|"error", "operation": ..., "outputs": {...}}
    """
    try:
        load_dotenv()
        file_config = get_file_config()

        operation, user_id, session_id, pdf_doc_id = extract_event_params(event)
        logger.info(f"Local entrypoint: op={operation} user={user_id} session={session_id} pdf={pdf_doc_id}")

        # Build context: paths + backend wired from config.ini source_type
        ctx = create_job_context(file_config, user_id, session_id, pdf_doc_id)
        logger.info(f"Storage backend: {ctx.source_type}")

        # Validate source inputs exist
        _validate_inputs(ctx)

        # Download inputs → /tmp/processing/
        _download_inputs(ctx)

        # Call operation — cleanup runs even if operation raises
        try:
            result = await _call_operation(operation, ctx, event, file_config)
        finally:
            cleanup_processing_directory(ctx.processing_dir)

        return {
            "status":    "success",
            "operation": operation,
            "outputs":   result.get("outputs", {}),
            "metadata":  result,
        }

    except Exception as e:
        logger.error(f"Local entrypoint error: {e}", exc_info=True)
        return {
            "status":    "error",
            "error":     str(e),
            "operation": event.get("operation"),
        }


def _validate_inputs(ctx) -> None:
    """Raise if required source inputs are missing."""
    missing = []
    if not ctx.file_exists(ctx.source_input_pdf):
        missing.append(ctx.source_input_pdf)
    if not ctx.file_exists(ctx.source_input_json):
        missing.append(ctx.source_input_json)
    if missing:
        raise FileNotFoundError(f"Required input files not found: {missing}")
    logger.info(f"Inputs validated: {ctx.source_input_pdf}, {ctx.source_input_json}")


def _download_inputs(ctx) -> None:
    """Download source inputs to local processing paths."""
    os.makedirs(os.path.dirname(ctx.local_input_pdf), exist_ok=True)
    ctx.download_file(ctx.source_input_pdf,  ctx.local_input_pdf)
    ctx.download_file(ctx.source_input_json, ctx.local_input_json)
    logger.info("Inputs downloaded to processing dir")


async def _call_operation(
    operation: str,
    ctx,
    event: Dict[str, Any],
    file_config,
) -> Dict[str, Any]:
    """Dispatch to the appropriate operation handler."""

    user_id    = event['user_id']
    session_id = event['session_id']
    pdf_doc_id = event['pdf_doc_id']

    mapping_config = {
        "llm_model":            file_config.get('mapping', 'llm_model',            fallback='gpt-4o'),
        "llm_temperature":      float(file_config.get('mapping', 'llm_temperature', fallback='0.05')),
        "llm_max_tokens":       int(file_config.get('mapping',   'llm_max_tokens',  fallback='8192')),
        "confidence_threshold": float(file_config.get('mapping', 'confidence_threshold', fallback='0.7')),
        "chunking_strategy":    file_config.get('mapping', 'chunking_strategy',    fallback='page'),
    }

    if operation == "make_embed_file":
        use_second_mapper_default = (
            file_config.get('mapping', 'use_second_mapper', fallback='false').lower() == 'true'
        )
        use_second_mapper = event.get('use_second_mapper', use_second_mapper_default)
        logger.info(f"Dual mapper: {use_second_mapper}")

        return await operations.handle_make_embed_file_operation(
            config=ctx,
            user_id=user_id,
            pdf_doc_id=pdf_doc_id,
            session_id=session_id,
            investor_type=event.get('investor_type'),
            mapping_config=mapping_config,
            use_second_mapper=use_second_mapper,
        )

    if operation == "fill_pdf":
        return await operations.handle_fill_pdf_operation(
            config=ctx,
            user_id=user_id,
            session_id=session_id,
            pdf_doc_id=pdf_doc_id,
        )

    if operation == "run_all":
        return await operations.handle_run_all_operation(
            input_pdf=ctx.local_input_pdf,
            input_json=ctx.local_input_json,
            mapping_config=mapping_config,
            user_id=user_id,
            session_id=session_id,
            pdf_doc_id=pdf_doc_id,
        )

    raise ValueError(f"Unknown operation: {operation!r}")
