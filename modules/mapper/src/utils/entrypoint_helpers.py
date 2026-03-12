"""
Shared utilities for entrypoint configuration and path building.

This module provides reusable functions for all entrypoints (local, AWS Lambda, HTTP server, etc.)
to avoid code duplication in path building and storage config creation.
"""

import os
import shutil
from typing import Dict, Any, Optional
from src.core.logger import logger


# ── New clean API ────────────────────────────────────────────────────────────

def create_job_context(file_config, user_id: int, session_id: str, pdf_doc_id: int):
    """
    Build a JobContext for one processing job.

    This is the single entry point for wiring storage backend + path resolution.
    Replaces the old build_all_file_paths() + create_storage_config_from_paths() pair.

    Args:
        file_config:  FileConfig instance (loaded from config.ini)
        user_id:      User ID
        session_id:   Session ID
        pdf_doc_id:   PDF document ID

    Returns:
        JobContext ready to pass to operations.handle_*()

    Example:
        ctx = create_job_context(file_config, 553, "086d...", 990)
        # Download inputs
        ctx.download_file(ctx.source_input_pdf, ctx.local_input_pdf)
        ctx.download_file(ctx.source_input_json, ctx.local_input_json)
        # Call operation
        result = await operations.handle_make_embed_file_operation(config=ctx, ...)
    """
    from src.storage.paths.resolver import PathResolver
    from src.storage.backends.factory import get_storage_backend
    from src.storage.job_context import JobContext

    source_type = file_config.get_source_type()
    backend     = get_storage_backend(source_type)
    resolver    = PathResolver(file_config)
    return JobContext(backend, resolver, user_id, session_id, pdf_doc_id)


# ── Legacy API (kept for backward compatibility) ─────────────────────────────


def build_all_file_paths(
    file_config,
    user_id: int,
    session_id: str,
    pdf_doc_id: int,
    processing_dir: Optional[str] = None
) -> Dict[str, str]:
    """
    Build all file paths needed for processing.
    
    This centralizes path building logic used by all entrypoints.
    
    Args:
        file_config: FileConfig instance for path generation
        user_id: User ID
        session_id: Session ID
        pdf_doc_id: PDF document ID
        processing_dir: Optional override for processing directory
        
    Returns:
        Dictionary with all file paths:
        - processing_dir
        - source_input_* (pdf, json, registry)
        - processing_* (all temp files)
        - source_output_* (all output files)
    """
    paths = {}
    
    # Processing directory (Docker local / Lambda temp)
    if processing_dir is None:
        processing_dir = file_config.get('local', 'processing_dir', fallback='/tmp/processing')
    paths['processing_dir'] = processing_dir
    
    # Ensure processing directory exists
    os.makedirs(paths['processing_dir'], exist_ok=True)
    
    # ========================================
    # SOURCE INPUT PATHS (where files come from)
    # ========================================
    paths['source_input_pdf'] = file_config.get_source_input_path(
        'pdf', user_id, session_id, pdf_doc_id
    )
    paths['source_input_json'] = file_config.get_source_input_path(
        'json', user_id, session_id, pdf_doc_id
    )
    paths['source_registry'] = file_config.get_source_input_path(
        'registry', user_id, session_id, pdf_doc_id
    )
    
    # ========================================
    # PROCESSING PATHS (where operations work - /tmp/processing/)
    # ========================================
    processing_paths = file_config.get_all_processing_paths(
        user_id, session_id, pdf_doc_id
    )
    paths.update(processing_paths)
    
    # ========================================
    # SOURCE OUTPUT PATHS (where results go - source storage)
    # ========================================
    
    # Core output files (extract, map, embed, fill)
    paths['source_output_extracted'] = file_config.get_source_output_path(
        'extracted_json', user_id, session_id, pdf_doc_id
    )
    paths['source_output_mapped'] = file_config.get_source_output_path(
        'mapped_json', user_id, session_id, pdf_doc_id
    )
    paths['source_output_radio'] = file_config.get_source_output_path(
        'radio_groups_json', user_id, session_id, pdf_doc_id
    )
    paths['source_output_embedded'] = file_config.get_source_output_path(
        'embedded_pdf', user_id, session_id, pdf_doc_id
    )
    paths['source_output_filled'] = file_config.get_source_output_path(
        'filled_pdf', user_id, session_id, pdf_doc_id
    )
    
    # Dual mapper output paths (semantic + RAG mapper)
    paths['source_output_semantic_mapping'] = file_config.get_source_output_path(
        'semantic_mapping_json', user_id, session_id, pdf_doc_id
    )
    paths['source_output_headers'] = file_config.get_source_output_path(
        'headers_with_fields_json', user_id, session_id, pdf_doc_id
    )
    paths['source_output_final_fields'] = file_config.get_source_output_path(
        'final_form_fields_json', user_id, session_id, pdf_doc_id
    )
    paths['source_output_header_file'] = file_config.get_source_output_path(
        'header_file_json', user_id, session_id, pdf_doc_id
    )
    paths['source_output_section_file'] = file_config.get_source_output_path(
        'section_file_json', user_id, session_id, pdf_doc_id
    )
    paths['source_output_java_mapping'] = file_config.get_source_output_path(
        'java_mapping', user_id, session_id, pdf_doc_id
    )
    paths['source_output_final_predictions'] = file_config.get_source_output_path(
        'final_predictions', user_id, session_id, pdf_doc_id
    )
    paths['source_output_llm_predictions'] = file_config.get_source_output_path(
        'llm_predictions', user_id, session_id, pdf_doc_id
    )
    paths['source_output_rag_predictions'] = file_config.get_source_output_path(
        'rag_predictions', user_id, session_id, pdf_doc_id
    )
    
    # Cache registry path
    paths['source_output_cache_registry'] = file_config.get_source_output_path(
        'cache_registry_json', user_id, session_id, pdf_doc_id
    )
    
    return paths


def create_storage_config_from_paths(
    paths: Dict[str, str],
    source_type: str = 'local'
) -> Any:
    """
    Create a storage config object from file paths.
    
    This sets up the config that operations.py expects, with all paths pre-configured.
    
    Args:
        paths: Dictionary from build_all_file_paths()
        source_type: Storage type ('local', 'aws', 'azure', 'gcp')
        
    Returns:
        Storage config object (LocalStorageConfig, AWSStorageConfig, etc.)
    """
    if source_type == 'local':
        from src.configs.local import LocalStorageConfig
        config = LocalStorageConfig()
    elif source_type == 'aws':
        from src.configs.aws import AWSStorageConfig
        config = AWSStorageConfig()
    elif source_type == 'azure':
        from src.configs.azure import AzureStorageConfig
        config = AzureStorageConfig()
    elif source_type == 'gcp':
        from src.configs.gcp import GCPStorageConfig
        config = GCPStorageConfig()
    else:
        raise ValueError(f"Unknown source_type: {source_type}")
    
    # Set source type
    config.source_type = source_type
    
    # ========================================
    # INPUT PATHS (from source storage)
    # ========================================
    config.source_input_pdf = paths.get('source_input_pdf')  # Keep original source path
    config.source_input_json = paths.get('source_input_json')  # Keep original source path
    config.local_input_pdf = paths.get('source_input_pdf')
    config.local_input_json = paths.get('source_input_json')
    config.local_global_json = paths.get('source_input_json')  # Alias
    
    # For cloud storage, set S3/Azure/GCS paths
    if source_type == 'aws':
        config.s3_input_pdf = paths.get('source_input_pdf')
        config.s3_input_json = paths.get('source_input_json')
        config.s3_global_json = paths.get('source_input_json')
    
    # ========================================
    # PROCESSING PATHS (temp files in /tmp/processing/)
    # ========================================
    config.local_input_pdf = paths.get('processing_input_pdf')  # Override with processing path for operations
    config.local_input_json = paths.get('processing_input_json')
    config.local_extracted_json = paths.get('extracted_json')
    config.local_mapped_json = paths.get('mapped_json')
    config.local_radio_json = paths.get('radio_groups_json')
    config.local_embedded_pdf = paths.get('embedded_pdf')
    config.local_filled_pdf = paths.get('filled_pdf')
    
    # Dual mapper processing paths
    config.local_semantic_mapping = paths.get('semantic_mapping')
    config.local_headers_with_fields = paths.get('headers_with_fields')
    config.local_final_form_fields = paths.get('final_form_fields')
    config.local_header_file = paths.get('header_file')
    config.local_section_file = paths.get('section_file')
    config.local_java_mapping = paths.get('java_mapping')
    config.local_final_predictions = paths.get('final_predictions')
    config.local_llm_predictions = paths.get('llm_predictions')
    config.local_rag_predictions = paths.get('rag_predictions')
    
    # Cache registry
    config.local_cache_registry = paths.get('cache_registry')
    
    # ========================================
    # OUTPUT DESTINATION PATHS (where to save results)
    # ========================================
    config.dest_extracted_json = paths.get('source_output_extracted')
    config.dest_mapped_json = paths.get('source_output_mapped')
    config.dest_radio_json = paths.get('source_output_radio')
    config.dest_embedded_pdf = paths.get('source_output_embedded')
    config.dest_filled_pdf = paths.get('source_output_filled')
    config.dest_semantic_mapping_json = paths.get('source_output_semantic_mapping')
    config.dest_headers_with_fields_json = paths.get('source_output_headers')
    config.dest_final_form_fields_json = paths.get('source_output_final_fields')
    config.dest_header_file_json = paths.get('source_output_header_file')
    config.dest_section_file_json = paths.get('source_output_section_file')
    config.dest_cache_registry_json = paths.get('source_output_cache_registry')
    config.dest_java_mapping_json = paths.get('source_output_java_mapping')
    config.dest_final_predictions_json = paths.get('source_output_final_predictions')
    config.dest_llm_predictions_json = paths.get('source_output_llm_predictions')
    config.dest_rag_predictions_json = paths.get('source_output_rag_predictions')
    
    return config


def prepare_input_files(
    paths: Dict[str, str],
    file_config
) -> None:
    """
    Copy input files from source storage to processing directory.
    
    Args:
        paths: Dictionary from build_all_file_paths()
        file_config: FileConfig instance
    """
    # Copy input PDF
    if os.path.exists(paths['source_input_pdf']):
        shutil.copy2(paths['source_input_pdf'], paths['processing_input_pdf'])
        logger.info(f"📥 Copied input PDF: {paths['source_input_pdf']} → {paths['processing_input_pdf']}")
    else:
        logger.warning(f"⚠️  Input PDF not found: {paths['source_input_pdf']}")
    
    # Copy input JSON
    if os.path.exists(paths['source_input_json']):
        shutil.copy2(paths['source_input_json'], paths['processing_input_json'])
        logger.info(f"📥 Copied input JSON: {paths['source_input_json']} → {paths['processing_input_json']}")
    else:
        logger.warning(f"⚠️  Input JSON not found: {paths['source_input_json']}")


def cleanup_processing_directory(processing_dir: str) -> None:
    """
    Clean up temporary processing directory.
    
    Args:
        processing_dir: Path to processing directory to clean
    """
    if os.path.exists(processing_dir):
        try:
            shutil.rmtree(processing_dir)
            logger.info(f"🧹 Cleaned up processing directory: {processing_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup processing directory: {e}")


def validate_input_files(paths: Dict[str, str]) -> None:
    """
    Validate that all required input files exist.
    
    Args:
        paths: Dictionary from build_all_file_paths()
        
    Raises:
        FileNotFoundError: If required input file is missing
    """
    required_files = {
        'source_input_pdf': 'Input PDF file',
        'source_input_json': 'Input JSON file'
    }
    
    for path_key, description in required_files.items():
        path = paths.get(path_key)
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"{description} not found: {path}")
    
    logger.info("✅ All required input files validated")


def extract_event_params(event: Dict[str, Any]) -> tuple:
    """
    Extract common parameters from event dictionary.
    
    Args:
        event: Event dictionary from HTTP request or Lambda
        
    Returns:
        Tuple of (operation, user_id, session_id, pdf_doc_id)
    """
    operation = event.get('operation', 'make_embed_file')
    user_id = event.get('user_id')
    session_id = event.get('session_id')
    pdf_doc_id = event.get('pdf_doc_id')
    
    # Validate required parameters
    if not user_id:
        raise ValueError("user_id is required")
    if not pdf_doc_id:
        raise ValueError("pdf_doc_id is required")
    if not session_id:
        raise ValueError("session_id is required")
    
    return operation, user_id, session_id, pdf_doc_id
