"""
Local deployment entrypoint.

This module handles local deployment where:
1. Files are copied from /app/data/input/ → /tmp/processing/
2. Operations process files in /tmp/processing/
3. Results are copied from /tmp/processing/ → /app/data/output/
4. Temp files in /tmp/processing/ are deleted (like Lambda ephemeral storage)
"""

import os
import shutil
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

from src.configs.file_config import get_file_config
from src.configs.local import LocalStorageConfig
from src.handlers import operations
from src.core.logger import logger
from src.utils.entrypoint_helpers import (
    build_all_file_paths,
    create_storage_config_from_paths,
    prepare_input_files,
    cleanup_processing_directory,
    validate_input_files,
    extract_event_params
)


async def handle_local_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle local deployment event.
    
    This is the main entry point for local deployment, analogous to AWS Lambda handler.
    Uses shared utilities from entrypoint_helpers to avoid code duplication.
    
    Flow:
        1. Load config.ini and .env
        2. Build file paths from patterns (via entrypoint_helpers)
        3. Validate input files exist (via entrypoint_helpers)
        4. Copy files from source to processing (via entrypoint_helpers)
        5. Create storage config (via entrypoint_helpers)
        6. Call operations (source-agnostic orchestrator)
        7. Copy results from processing to source
        8. Cleanup temp files (via entrypoint_helpers)
        9. Return result with source paths
    
    Args:
        event: Event dictionary with:
            - operation: "make_embed_file", "fill_pdf", "run_all", etc.
            - user_id: User ID
            - session_id: Session ID
            - pdf_doc_id: PDF document ID
            - investor_type: Optional investor type
            - use_second_mapper: Optional boolean for RAG
    
    Returns:
        Result dictionary with:
            - status: "success" or "error"
            - output_paths: Dictionary of output file paths in source storage
            - metadata: Processing metadata
    
    Example:
        event = {
            "operation": "make_embed_file",
            "user_id": 553,
            "session_id": "086d6670-81e5-47f4-aecb-e4f7c3ba2a83",
            "pdf_doc_id": 990,
            "investor_type": "individual",
            "use_second_mapper": True
        }
        
        result = handle_local_event(event)
        # Returns: {"status": "success", "output_paths": {...}, ...}
    """
    try:
        logger.info(f"Local entrypoint: Processing event {event.get('operation')}")
        
        # 1. Load configuration
        load_dotenv()
        file_config = get_file_config()
        
        # 2. Extract event parameters using shared utility
        operation, user_id, session_id, pdf_doc_id = extract_event_params(event)
        use_second_mapper = event.get('use_second_mapper', False)
        
        logger.info(f"Processing: user={user_id}, session={session_id}, pdf={pdf_doc_id}")
        
        # 3. Build all file paths using shared utility
        paths = build_all_file_paths(file_config, user_id, session_id, pdf_doc_id)
        logger.debug(f"File paths built: {paths}")
        
        # 4. Validate input files exist using shared utility
        logger.info("=" * 60)
        logger.info("VALIDATING INPUT FILES")
        logger.info("=" * 60)
        
        try:
            validate_input_files(paths)
            
            # Log file sizes for confirmation
            pdf_size = os.path.getsize(paths['source_input_pdf'])
            json_size = os.path.getsize(paths['source_input_json'])
            logger.info(f"✅ Input PDF: {paths['source_input_pdf']} ({pdf_size:,} bytes)")
            logger.info(f"✅ Input JSON: {paths['source_input_json']} ({json_size:,} bytes)")
            
        except FileNotFoundError as e:
            # Enhance error message with helpful instructions
            input_base = file_config.get('local', 'input_base_path', fallback='data/input')
            error_msg = str(e) + "\n"
            error_msg += f"\n📝 Please place your files in: {input_base}/\n"
            error_msg += f"\n   Expected file names:\n"
            error_msg += f"   - {user_id}_{session_id}_{pdf_doc_id}.pdf\n"
            error_msg += f"   - {user_id}_{session_id}_{pdf_doc_id}.json\n"
            error_msg += "\n" + "=" * 60 + "\n"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        logger.info("=" * 60)
        
        # 5. Prepare input files using shared utility
        prepare_input_files(paths, file_config)
        
        # 6. Create storage config using shared utility
        config = create_storage_config_from_paths(paths, source_type='local')
        
        # 7. Call orchestrator (source-agnostic!)
        result = await _call_operation(
            operation=operation,
            config=config,
            event=event
        )
        
        # 8. Save results (copy from processing to source)
        output_paths = _save_results(result, paths, file_config, user_id, session_id, pdf_doc_id)
        
        # 9. Cleanup temp files using shared utility
        cleanup_processing_directory(paths['processing_dir'])
        
        # 10. Return result with source paths
        return {
            "status": "success",
            "operation": operation,
            "output_paths": output_paths,
            "metadata": result
        }
        
    except Exception as e:
        logger.error(f"Local entrypoint error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "operation": event.get('operation')
        }


async def _call_operation(
    operation: str,
    config: LocalStorageConfig,
    event: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Call the appropriate operation handler.
    
    This is source-agnostic - operations only work with local paths.
    """
    logger.info(f"Calling operation: {operation}")
    
    user_id = event['user_id']
    session_id = event['session_id']
    pdf_doc_id = event['pdf_doc_id']
    
    if operation == "make_embed_file":
        # Build mapping config from config.ini
        from src.configs.file_config import get_file_config
        file_config = get_file_config()
        mapping_config = {
            "llm_model": file_config.get('mapping', 'llm_model', fallback='gpt-4o'),
            "llm_temperature": float(file_config.get('mapping', 'llm_temperature', fallback='0.05')),
            "llm_max_tokens": int(file_config.get('mapping', 'llm_max_tokens', fallback='8192')),
            "confidence_threshold": float(file_config.get('mapping', 'confidence_threshold', fallback='0.7')),
            "chunking_strategy": file_config.get('mapping', 'chunking_strategy', fallback='page'),
        }
        
        # Use second mapper: event value overrides config.ini
        use_second_mapper_default = file_config.get('mapping', 'use_second_mapper', fallback='false').lower() == 'true'
        use_second_mapper = event.get('use_second_mapper', use_second_mapper_default)
        
        logger.info(f"🔀 Dual mapper mode: {use_second_mapper} (event={event.get('use_second_mapper')}, config.ini={use_second_mapper_default})")
        
        result = await operations.handle_make_embed_file_operation(
            config=config,
            user_id=user_id,
            pdf_doc_id=pdf_doc_id,
            session_id=session_id,
            investor_type=event.get('investor_type'),
            mapping_config=mapping_config,
            use_second_mapper=use_second_mapper
        )
        
    elif operation == "fill_pdf":
        result = await operations.handle_fill_pdf_operation(
            config=config,
            user_id=user_id,
            session_id=session_id,
            pdf_doc_id=pdf_doc_id
        )
        
    elif operation == "run_all":
        # Build mapping config from config.ini
        from src.configs.file_config import get_file_config
        file_config = get_file_config()
        mapping_config = {
            "llm_model": file_config.get('mapping', 'llm_model', fallback='gpt-4o'),
            "llm_temperature": float(file_config.get('mapping', 'llm_temperature', fallback='0.05')),
            "llm_max_tokens": int(file_config.get('mapping', 'llm_max_tokens', fallback='8192')),
            "confidence_threshold": float(file_config.get('mapping', 'confidence_threshold', fallback='0.7')),
            "chunking_strategy": file_config.get('mapping', 'chunking_strategy', fallback='page'),
        }
        
        result = await operations.handle_run_all_operation(
            input_pdf=config.local_input_pdf,
            input_json=config.local_input_json,
            mapping_config=mapping_config,
            user_id=user_id,
            session_id=session_id,
            pdf_doc_id=pdf_doc_id
        )
        
    else:
        raise ValueError(f"Unknown operation: {operation}")
    
    logger.info(f"Operation {operation} completed successfully")
    return result


def _save_results(
    result: Dict[str, Any],
    paths: Dict[str, str],
    file_config,
    user_id: int,
    session_id: str,
    pdf_doc_id: int
) -> Dict[str, str]:
    """
    Extract output file paths from operation results.
    
    NOTE: Files are ALREADY saved by operations via OutputFileHandler.
    This function just extracts paths for verification/response.
    
    Returns dictionary of output paths in source storage.
    """
    logger.info("Extracting output paths from operation results...")
    
    output_paths = {}
    
    # Handle make_embed_file operation output
    if 'outputs' in result:
        outputs = result['outputs']
        
        # Map output keys to paths (files already saved by operations)
        if 'extracted_json' in outputs and outputs['extracted_json']:
            output_paths['extracted_json'] = paths['source_output_extracted']
        
        if 'mapping_json' in outputs and outputs['mapping_json']:
            output_paths['mapping_json'] = paths['source_output_mapped']
        
        if 'radio_groups_json' in outputs and outputs['radio_groups_json']:
            output_paths['radio_groups_json'] = paths['source_output_radio']
        
        if 'embedded_pdf' in outputs and outputs['embedded_pdf']:
            output_paths['embedded_pdf'] = paths['source_output_embedded']
        
        if 'semantic_mapping_json' in outputs and outputs['semantic_mapping_json']:
            output_paths['semantic_mapping_json'] = paths['source_output_semantic_mapping']
        
        if 'headers_with_fields' in outputs and outputs['headers_with_fields']:
            output_paths['headers_with_fields'] = paths['source_output_headers']
        
        if 'final_form_fields' in outputs and outputs['final_form_fields']:
            output_paths['final_form_fields'] = paths['source_output_final_fields']
    
    # Legacy support: Handle old-style embedded_pdf_path key
    elif 'embedded_pdf_path' in result:
        output_paths['embedded_pdf'] = paths['source_output_embedded']
    
    # Legacy support: Handle fill operation
    if 'filled_pdf_path' in result:
        output_paths['filled_pdf'] = paths['source_output_filled']
    
    logger.info(f"✅ Extracted {len(output_paths)} output paths (files already saved by operations)")
    return output_paths



