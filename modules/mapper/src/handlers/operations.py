"""
Core operation handlers - source-agnostic business logic.

These handlers work with ANY storage backend (AWS S3, Azure Blob, GCS, local filesystem).
They use the universal storage helpers for download/upload operations.

Platform-specific wrappers (lambda_handler.py, azure_function.py, etc.) call these functions.
"""

import os
import time
import json
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from src.core.config import get_complete_file_config, get_processing_output_config
from src.utils.storage_helper import (
    download_from_source,
    upload_to_source,
    file_exists,
    create_storage_config,
    get_storage_type
)
from src.handlers.file_handlers import create_file_handlers
from src.extractors.detailed_fitz import DetailedFitzExtractor
from src.mappers.semantic_mapper import SemanticMapper
from src.embedders.embed_keys import run_embed_java_stage
from src.fillers.fill_pdf import fill_with_java
from src.utils.map_time_estimator import estimate_map_stage_time

# Import notification system (optional)
try:
    from adapter_src.notifier import (
        PipelineNotifier,
        PipelineStage,
        StageStatus,
        NotificationLevel
    )
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    PipelineNotifier = None

logger = logging.getLogger(__name__)


async def safe_notify(notifier, operation_name: str, *args, **kwargs) -> bool:
    """Safely send notification without failing the pipeline."""
    if not notifier or not NOTIFICATIONS_AVAILABLE:
        return False
    
    try:
        if operation_name == "stage_completion":
            return await notifier.notify_stage_completion(*args, **kwargs)
        elif operation_name == "pipeline_completion":
            return await notifier.notify_pipeline_completion(*args, **kwargs)
        else:
            logger.warning(f"Unknown notification operation: {operation_name}")
            return False
    except Exception as e:
        logger.warning(f"Notification failed for {operation_name}: {e}")
        return False


async def handle_extract_operation(
    config,  # Storage config (first parameter)
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    notifier: Optional[Any] = None,
    pdf_doc_id: Optional[int] = None,
    input_json_doc_id: Optional[int] = None,
    input_json_path: Optional[str] = None,
    mapping_config: Optional[dict] = None
) -> Dict[str, Any]:
    """
    Extract form fields from PDF - works with ANY storage backend.
    
    Args:
        config: Storage config with pre-configured paths
        user_id: Optional user ID for tracking
        session_id: Optional session ID for tracking
        notifier: Optional notification system
        pdf_doc_id: Optional PDF document ID
        input_json_doc_id: Optional input JSON document ID
        input_json_path: Optional input JSON path for pre-map estimation
        mapping_config: Optional mapping config for pre-map estimation
        
    Returns:
        Operation result with output file path
    """
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("EXTRACT OPERATION")
    logger.info("=" * 60)
    logger.info(f"Storage type: {config.source_type}")
    logger.info(f"User ID: {user_id}, Session ID: {session_id}")
    
    user_input_details = {
        "user_id": user_id,
        "pdf_doc_id": pdf_doc_id,
        "input_json_doc_id": input_json_doc_id,
        "session_id": session_id
    }
    
    try:
        # Create file handlers
        input_handler, output_handler = create_file_handlers(config)
        
        # Get input PDF (already downloaded by entrypoint)
        local_pdf = input_handler.get_input('input_pdf')
        if not local_pdf:
            raise FileNotFoundError("Input PDF not available")
        
        logger.info(f"Input PDF: {local_pdf}")
        
        # Initialize extractor
        extractor_config = {
            "WIDGET_LINE_DISTANCE_THRESHOLD": 10,
            "rounding": 1
        }
        extractor = DetailedFitzExtractor(extractor_config)
        
        # Extract to configured path
        extraction_output_path = config.local_extracted_json
        storage_config = {
            "type": "local",
            "path": extraction_output_path
        }
        
        # Extract from PDF
        result = extractor.extract(
            pdf_path=local_pdf,
            storage_config=storage_config
        )
        
        # Save output immediately to source storage
        saved_path = output_handler.save_output(extraction_output_path, 'extracted_json')
        if saved_path:
            logger.info(f"✅ Saved extraction to: {saved_path}")
        
        # Get PDF hash
        pdf_hash = result.get('pdf_hash')
        if pdf_hash:
            logger.info(f"PDF fingerprint hash: {pdf_hash[:16]}...")
        
        # Optional: pre-compute map stage estimate
        pre_map_time_estimate = None
        if input_json_path:
            try:
                pre_map_time_estimate = estimate_map_stage_time(
                    extracted_json_path=extraction_output_path,
                    input_json_path=input_json_path,
                    mapping_config=mapping_config or {}
                )
                logger.info(f"Pre-map estimate: {pre_map_time_estimate.get('status')}")
            except Exception as estimate_error:
                logger.warning(f"Failed pre-map estimate: {estimate_error}")
                pre_map_time_estimate = {"status": "error", "error": str(estimate_error)}
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Send success notification
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.EXTRACT,
                status=StageStatus.COMPLETED,
                execution_time=duration,
                input_files={"pdf": local_pdf},
                output_files={"extracted_json": extraction_output_path},
                user_input_details=user_input_details,
                metadata={
                    "storage_type": config.source_type,
                    "extractor_config": extractor_config,
                    "fields_extracted": len(result.get("fields", [])) if isinstance(result, dict) else None,
                    "pre_map_time_estimate": pre_map_time_estimate
                }
            )
        
        logger.info(f"✅ Extraction completed in {duration}s")
        logger.info("=" * 60)
        
        response = {
            "operation": "extract",
            "output_file": extraction_output_path,
            "storage_type": config.source_type,
            "status": "success",
            "execution_time_seconds": duration,
            "pdf_hash": pdf_hash
        }
        
        if pre_map_time_estimate:
            response["pre_map_time_estimate"] = pre_map_time_estimate
        
        return response
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Send failure notification
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.EXTRACT,
                status=StageStatus.FAILED,
                execution_time=duration,
                error_message=str(e),
                level=NotificationLevel.CRITICAL,
                user_input_details=user_input_details,
                metadata={"storage_type": config.source_type, "error_type": type(e).__name__}
            )
        
        logger.error(f"❌ Extraction failed after {duration}s: {str(e)}")
        raise


async def handle_map_operation(
    config,  # Storage config (first parameter)
    mapping_config: dict,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    notifier: Optional[Any] = None,
    pdf_doc_id: Optional[int] = None,
    input_json_doc_id: Optional[int] = None,
    investor_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Semantic mapping operation - works with ANY storage backend.
    
    Args:
        config: Storage config with pre-configured paths
        mapping_config: Mapping configuration
        user_id: Optional user ID
        session_id: Optional session ID
        notifier: Optional notification system
        pdf_doc_id: Optional PDF document ID
        input_json_doc_id: Optional input JSON document ID
        investor_type: Optional investor type
        
    Returns:
        Operation result with output files
    """
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("MAP OPERATION")
    logger.info("=" * 60)
    logger.info(f"Storage type: {config.source_type}")
    logger.info(f"User ID: {user_id}, Session ID: {session_id}")
    logger.info(f"Investor Type: {investor_type}")
    
    user_input_details = {
        "user_id": user_id,
        "pdf_doc_id": pdf_doc_id,
        "input_json_doc_id": input_json_doc_id,
        "session_id": session_id,
        "investor_type": investor_type
    }
    
    try:
        # Create file handlers
        input_handler, output_handler = create_file_handlers(config)
        
        # Get input files (already downloaded by entrypoint)
        local_extracted = input_handler.get_input('extracted_json')
        local_input = input_handler.get_input('input_json')
        
        if not local_extracted or not local_input:
            raise FileNotFoundError("Required input files not available")
        
        logger.info(f"Extracted JSON: {local_extracted}")
        logger.info(f"Input JSON: {local_input}")
        
        # Initialize mapper - use llm_model from settings (LiteLLM format)
        from src.core.config import settings
        mapper = SemanticMapper(
            llm_provider=mapping_config.get("llm_model", settings.llm_model),
            confidence_threshold=mapping_config.get("confidence_threshold", 0.7),
            chunking_strategy=mapping_config.get("chunking_strategy", "page")
        )
        
        # Use configured output paths
        local_mapping = config.local_mapped_json
        local_radio = config.local_radio_json
        
        # Debug: Check if paths are set
        if not local_mapping or not local_radio:
            logger.error(f"❌ Config paths not set!")
            logger.error(f"   local_mapped_json: {local_mapping}")
            logger.error(f"   local_radio_json: {local_radio}")
            raise ValueError(f"Config missing paths: local_mapped_json={local_mapping}, local_radio_json={local_radio}")
        
        logger.info(f"Output paths configured:")
        logger.info(f"   Mapping: {local_mapping}")
        logger.info(f"   Radio groups: {local_radio}")
        
        storage_config = {
            "output_path": local_mapping,
            "radio_groups": local_radio
        }
        
        # Perform mapping
        mapping_result = await mapper.process_and_save(
            extracted_path=local_extracted,
            input_json_path=local_input,
            original_pdf_path="",
            storage_config=storage_config,
            investor_type=investor_type
        )
        
        # The semantic mapper outputs dictionary format with wrapper: {"user_id": ..., "predictions": {...}}
        # Save this as semantic_mapping.json for reference/debugging/caching
        semantic_path = local_mapping.replace("_mapped_fields.json", "_semantic_mapping.json")
        logger.info(f"💾 Saving semantic mapper output (for cache): {semantic_path}")
        shutil.copy2(local_mapping, semantic_path)
        
        # Now convert to Java-compatible format for the embedder
        # Java embedder needs array format without wrapper: {"field_id": ["field_name", "", confidence]}
        logger.info("🔄 Converting semantic mapping to Java-compatible format...")
        with open(local_mapping, 'r') as f:
            semantic_data = json.load(f)
        
        # Strip wrapper if present
        if isinstance(semantic_data, dict) and "predictions" in semantic_data:
            semantic_mappings = semantic_data["predictions"]
        else:
            semantic_mappings = semantic_data
        
        # Convert to Java array format
        java_mapping = {}
        for field_id, mapping_data in semantic_mappings.items():
            if isinstance(mapping_data, dict):
                field_name = mapping_data.get("predicted_field_name")
                confidence = mapping_data.get("confidence", 0.0)
                java_mapping[field_id] = [field_name, "", confidence] if field_name else [None, None, 0]
            elif isinstance(mapping_data, list) and len(mapping_data) >= 3:
                field_name = mapping_data[0]
                confidence = mapping_data[2]
                java_mapping[field_id] = [field_name, "", confidence] if field_name else [None, None, 0]
            elif mapping_data is None:
                java_mapping[field_id] = [None, None, 0]
            else:
                logger.warning(f"Field {field_id} has unexpected format: {mapping_data}")
                java_mapping[field_id] = [None, None, 0]
        
        # Save Java format to mapped_fields.json (for embedder)
        with open(local_mapping, 'w') as f:
            json.dump(java_mapping, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Converted {len(java_mapping)} fields to Java format → {local_mapping}")
        
        # Save outputs immediately to source storage
        # IMPORTANT: Save semantic mapping first (for cache), then Java format (for embedder)
        saved_semantic = output_handler.save_output(semantic_path, 'semantic_mapping_json')
        saved_mapping = output_handler.save_output(local_mapping, 'mapped_json')
        saved_radio = output_handler.save_output(local_radio, 'radio_json')
        
        if saved_semantic:
            logger.info(f"✅ Saved semantic mapping (for cache): {saved_semantic}")
        if saved_mapping:
            logger.info(f"✅ Saved Java mapping (for embedder): {saved_mapping}")
        if saved_radio:
            logger.info(f"✅ Saved radio groups to: {saved_radio}")
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Extract statistics
        field_stats = mapping_result.get("field_statistics", {})
        
        # Send success notification
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.MAP,
                status=StageStatus.COMPLETED,
                execution_time=duration,
                input_files={
                    "extracted_json": local_extracted,
                    "input_keys": local_input
                },
                output_files={
                    "mapping": local_mapping,
                    "radio_groups": local_radio
                },
                user_input_details=user_input_details,
                performance_metrics={
                    "total_fields_mapped": field_stats.get("total_fields_mapped", 0),
                    "high_confidence_count": field_stats.get("high_confidence_count", 0),
                    "storage_type": config.source_type
                }
            )
        
        logger.info(f"✅ Mapping completed in {duration}s")
        logger.info("=" * 60)
        
        return {
            "operation": "map",
            "mapping_result": {
                "mapping_path": local_mapping,  # Local processing path
                "radio_groups_path": local_radio,  # Local processing path
                "field_statistics": field_stats,
                # ADD: Destination paths for cache registration
                "dest_mapping_path": saved_mapping,  # Where file was saved (persistent)
                "dest_radio_groups_path": saved_radio  # Where file was saved (persistent)
            },
            "storage_type": config.source_type,
            "status": "success",
            "execution_time_seconds": duration
        }
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.MAP,
                status=StageStatus.FAILED,
                execution_time=duration,
                error_message=str(e),
                level=NotificationLevel.CRITICAL,
                user_input_details=user_input_details,
                metadata={"storage_type": config.source_type, "error_type": type(e).__name__}
            )
        
        logger.error(f"❌ Mapping failed after {duration}s: {str(e)}")
        raise


async def handle_embed_operation(
    config,  # Storage config (first parameter)
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    notifier: Optional[Any] = None,
    pdf_doc_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Embed operation - embeds form data into PDF using Java rebuilder.
    Works with ANY storage backend.
    
    Args:
        config: Storage config with pre-configured paths
        user_id: Optional user ID
        session_id: Optional session ID
        notifier: Optional notification system
        pdf_doc_id: Optional PDF document ID
        
    Returns:
        Operation result with embedded PDF path
    """
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("EMBED OPERATION")
    logger.info("=" * 60)
    logger.info(f"Storage type: {config.source_type}")
    logger.info(f"User ID: {user_id}, Session ID: {session_id}")
    
    user_input_details = {
        "user_id": user_id,
        "pdf_doc_id": pdf_doc_id,
        "session_id": session_id
    }
    
    try:
        # Create file handlers
        input_handler, output_handler = create_file_handlers(config)
        
        # Get input files
        # PDF and extracted JSON can be downloaded if needed
        local_pdf = input_handler.get_input('input_pdf')
        local_extracted = input_handler.get_input('extracted_json')
        
        # Mapped JSON and radio groups were created in THIS pipeline run,
        # so they're already at the config paths (not downloaded)
        local_mapping = config.local_mapped_json
        local_radio = config.local_radio_json
        
        if not all([local_pdf, local_extracted, local_mapping, local_radio]):
            missing = []
            if not local_pdf: missing.append("PDF")
            if not local_extracted: missing.append("extracted JSON")
            if not local_mapping: missing.append("mapping JSON")
            if not local_radio: missing.append("radio groups")
            raise FileNotFoundError(f"Required input files not available: {', '.join(missing)}")
        
        logger.info(f"Input PDF: {local_pdf}")
        logger.info(f"Extracted JSON: {local_extracted}")
        logger.info(f"Mapping JSON: {local_mapping}")
        logger.info(f"Radio groups: {local_radio}")
        
        # Use configured output path
        local_embedded = config.local_embedded_pdf
        storage_config = {
            "type": "local",
            "path": local_embedded
        }
        
        # Run Java embedder
        embedded_pdf = await run_embed_java_stage(
            original_pdf=local_pdf,
            extracted_json=local_extracted,
            mapping_json=local_mapping,
            radio_json=local_radio,
            storage_config=storage_config
        )
        
        # Save output immediately to source storage
        # Use the ACTUAL output path from Java embedder, not the config path
        logger.info(f"🔍 DEBUG: About to save embedded PDF:")
        logger.info(f"   embedded_pdf (actual output): {embedded_pdf}")
        logger.info(f"   config.dest_embedded_pdf: {config.dest_embedded_pdf}")
        
        saved_path = output_handler.save_output(embedded_pdf, 'embedded_pdf')
        
        logger.info(f"🔍 DEBUG: Save result:")
        logger.info(f"   saved_path: {saved_path}")
        
        if saved_path:
            logger.info(f"✅ Saved embedded PDF to: {saved_path}")
        else:
            logger.error(f"❌ Failed to save embedded PDF!")
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Send success notification
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.EMBED,
                status=StageStatus.COMPLETED,
                execution_time=duration,
                input_files={
                    "pdf": local_pdf,
                    "extracted": local_extracted,
                    "mapping": local_mapping,
                    "radio_groups": local_radio
                },
                output_files={"embedded_pdf": local_embedded},
                user_input_details=user_input_details,
                metadata={"storage_type": config.source_type}
            )
        
        logger.info(f"✅ Embedding completed in {duration}s")
        logger.info("=" * 60)
        
        return {
            "operation": "embed",
            "output_file": embedded_pdf,  # Actual output path from Java embedder
            "dest_output_file": saved_path,  # Destination path for cache registration
            "storage_type": config.source_type,
            "status": "success",
            "execution_time_seconds": duration
        }
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.EMBED,
                status=StageStatus.FAILED,
                execution_time=duration,
                error_message=str(e),
                level=NotificationLevel.CRITICAL,
                user_input_details=user_input_details,
                metadata={"storage_type": config.source_type, "error_type": type(e).__name__}
            )
        
        logger.error(f"❌ Embedding failed after {duration}s: {str(e)}")
        raise


async def handle_fill_operation(
    config,  # Storage config (first parameter)
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    notifier: Optional[Any] = None,
    pdf_doc_id: Optional[int] = None,
    input_json_doc_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fill operation - fills embedded PDF with user data using Java filler.
    Works with ANY storage backend.
    
    Args:
        config: Storage config with pre-configured paths
        user_id: Optional user ID
        session_id: Optional session ID
        notifier: Optional notification system
        pdf_doc_id: Optional PDF document ID
        input_json_doc_id: Optional input JSON document ID
        
    Returns:
        Operation result with filled PDF path
    """
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("FILL OPERATION")
    logger.info("=" * 60)
    logger.info(f"Storage type: {config.source_type}")
    logger.info(f"User ID: {user_id}, Session ID: {session_id}")
    
    user_input_details = {
        "user_id": user_id,
        "pdf_doc_id": pdf_doc_id,
        "input_json_doc_id": input_json_doc_id,
        "session_id": session_id
    }
    
    try:
        # Create file handlers
        input_handler, output_handler = create_file_handlers(config)
        
        # Get input files (already downloaded by entrypoint)
        local_embedded = input_handler.get_input('embedded_pdf')
        local_input = input_handler.get_input('input_json')
        
        if not local_embedded or not local_input:
            raise FileNotFoundError("Required input files not available")
        
        logger.info(f"Embedded PDF: {local_embedded}")
        logger.info(f"Input JSON: {local_input}")
        
        # Use configured output path
        local_filled = config.local_filled_pdf
        storage_config = {
            "type": "local",
            "path": local_filled
        }
        
        # Run Java filler
        filled_pdf = await fill_with_java(
            embedded_pdf=local_embedded,
            input_json=local_input,
            storage_config=storage_config
        )
        
        # Save output immediately to source storage
        saved_path = output_handler.save_output(local_filled, 'filled_pdf')
        if saved_path:
            logger.info(f"✅ Saved filled PDF to: {saved_path}")
        
        # Generate presigned URL for S3 files
        filled_presigned_url = None
        if config.source_type == "aws" and hasattr(config, 's3_filled_pdf'):
            try:
                from src.clients.s3_client import S3Client
                s3_client = S3Client()
                filled_presigned_url = s3_client.generate_presigned_url(saved_path, expires_in=3600)
                logger.info("✅ Generated presigned URL for filled PDF (expires in 1 hour)")
            except Exception as presign_error:
                logger.warning(f"Failed to generate presigned URL for filled PDF: {presign_error}")
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        # Send success notification
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.FILL,
                status=StageStatus.COMPLETED,
                execution_time=duration,
                input_files={
                    "embedded_pdf": local_embedded,
                    "input_json": local_input
                },
                output_files={"filled_pdf": local_filled},
                user_input_details=user_input_details,
                metadata={"storage_type": config.source_type}
            )
        
        logger.info(f"✅ Filling completed in {duration}s")
        logger.info("=" * 60)
        
        result = {
            "operation": "fill",
            "output_file": local_filled,
            "storage_type": config.source_type,
            "status": "success",
            "execution_time_seconds": duration
        }
        
        # Add presigned URL if available
        if filled_presigned_url:
            result["filled_presigned_url"] = filled_presigned_url
            logger.info(f"Presigned URL included in response")
        
        return result
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.FILL,
                status=StageStatus.FAILED,
                execution_time=duration,
                error_message=str(e),
                level=NotificationLevel.CRITICAL,
                user_input_details=user_input_details,
                metadata={"storage_type": config.source_type, "error_type": type(e).__name__}
            )
        
        logger.error(f"❌ Filling failed after {duration}s: {str(e)}")
        raise


async def handle_run_all_operation(
    input_pdf: str,
    input_json: str,
    mapping_config: dict,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    notifier: Optional[Any] = None,
    pdf_doc_id: Optional[int] = None,
    input_json_doc_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Run all operation - executes complete pipeline (extract → map → embed → fill).
    Works with ANY storage backend.
    
    Args:
        input_pdf: Input PDF path (s3://, gs://, azure://, or local)
        input_json: Input JSON with user data
        mapping_config: Mapping configuration
        user_id: Optional user ID
        session_id: Optional session ID
        notifier: Optional notification system
        pdf_doc_id: Optional PDF document ID
        input_json_doc_id: Optional input JSON document ID
        
    Returns:
        Complete pipeline result with all output files
    """
    start_time = time.time()
    storage_type = get_storage_type(input_pdf)
    
    logger.info("=" * 80)
    logger.info("RUN ALL OPERATION - COMPLETE PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Input PDF: {input_pdf}")
    logger.info(f"Input JSON: {input_json}")
    logger.info(f"Storage type: {storage_type}")
    
    pipeline_results = {}
    
    try:
        # Stage 1: Extract
        logger.info("\n[1/4] Starting EXTRACT stage...")
        extract_result = await handle_extract_operation(
            input_file=input_pdf,
            user_id=user_id,
            session_id=session_id,
            notifier=notifier,
            pdf_doc_id=pdf_doc_id,
            input_json_doc_id=input_json_doc_id,
            input_json_path=input_json,
            mapping_config=mapping_config
        )
        pipeline_results["extract"] = extract_result
        extracted_json = extract_result["output_file"]
        logger.info(f"✅ EXTRACT completed: {extracted_json}")
        
        # Stage 2: Map
        logger.info("\n[2/4] Starting MAP stage...")
        map_result = await handle_map_operation(
            config=config,  # Pass config instead of file paths
            mapping_config=mapping_config,
            user_id=user_id,
            session_id=session_id,
            notifier=notifier,
            pdf_doc_id=pdf_doc_id,
            input_json_doc_id=input_json_doc_id
        )
        pipeline_results["map"] = map_result
        mapping_json = map_result["mapping_result"]["mapping_path"]
        radio_groups = map_result["mapping_result"]["radio_groups_path"]
        logger.info(f"✅ MAP completed: {mapping_json}")
        
        # Stage 3: Embed
        logger.info("\n[3/4] Starting EMBED stage...")
        embed_result = await handle_embed_operation(
            config=config,  # Pass config instead of file paths
            user_id=user_id,
            session_id=session_id,
            notifier=notifier,
            pdf_doc_id=pdf_doc_id
        )
        pipeline_results["embed"] = embed_result
        embedded_pdf = embed_result["output_file"]
        logger.info(f"✅ EMBED completed: {embedded_pdf}")
        
        # Stage 4: Fill
        logger.info("\n[4/4] Starting FILL stage...")
        fill_result = await handle_fill_operation(
            embedded_pdf_path=embedded_pdf,
            input_json_path=input_json,
            user_id=user_id,
            session_id=session_id,
            notifier=notifier,
            pdf_doc_id=pdf_doc_id,
            input_json_doc_id=input_json_doc_id
        )
        pipeline_results["fill"] = fill_result
        filled_pdf = fill_result["output_file"]
        logger.info(f"✅ FILL completed: {filled_pdf}")
        
        # Pipeline complete
        end_time = time.time()
        total_duration = round(end_time - start_time, 2)
        
        # Send pipeline completion notification
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "pipeline_completion",
                status="completed",
                total_duration=total_duration,
                final_output=filled_pdf,
                stage_results=pipeline_results
            )
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ COMPLETE PIPELINE SUCCESS in {total_duration}s")
        logger.info("=" * 80)
        
        return {
            "operation": "run_all",
            "status": "success",
            "storage_type": storage_type,
            "total_execution_time_seconds": total_duration,
            "final_output": filled_pdf,
            "pipeline_results": pipeline_results
        }
        
    except Exception as e:
        end_time = time.time()
        total_duration = round(end_time - start_time, 2)
        
        # Send pipeline failure notification
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "pipeline_completion",
                status="failed",
                total_duration=total_duration,
                error_message=str(e),
                stage_results=pipeline_results
            )
        
        logger.error("\n" + "=" * 80)
        logger.error(f"❌ PIPELINE FAILED after {total_duration}s: {str(e)}")
        logger.error("=" * 80)
        raise


async def handle_refresh_operation(
    input_pdf: str,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    notifier: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Refresh operation - re-extracts data from PDF and updates config.
    Works with ANY storage backend.
    
    This is similar to extract but specifically for refreshing existing configs.
    
    Args:
        input_pdf: Input PDF path (s3://, gs://, azure://, or local)
        user_id: Optional user ID
        session_id: Optional session ID
        notifier: Optional notification system
        
    Returns:
        Operation result with refreshed extraction
    """
    start_time = time.time()
    storage_type = get_storage_type(input_pdf)
    
    logger.info("=" * 60)
    logger.info("REFRESH OPERATION")
    logger.info("=" * 60)
    logger.info(f"Input PDF: {input_pdf}")
    logger.info(f"Storage type: {storage_type}")
    logger.info("Re-extracting PDF data to refresh configuration...")
    
    try:
        # Call extract operation (refresh is essentially a re-extract)
        result = await handle_extract_operation(
            input_file=input_pdf,
            user_id=user_id,
            session_id=session_id,
            notifier=notifier
        )
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        logger.info(f"✅ Refresh completed in {duration}s")
        logger.info("=" * 60)
        
        return {
            "operation": "refresh",
            "status": "success",
            "storage_type": storage_type,
            "execution_time_seconds": duration,
            "refreshed_file": result["output_file"],
            "extraction_result": result
        }
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        logger.error(f"❌ Refresh failed after {duration}s: {str(e)}")
        raise


async def handle_make_embed_file_operation(
    config: Any,
    user_id: int,
    pdf_doc_id: int,
    session_id: Optional[int] = None,
    investor_type: str = 'individual',
    mapping_config: Optional[dict] = None,
    use_second_mapper: bool = False,
    notifier: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Make embed file operation - runs extract → map → embed pipeline (without fill).
    Uses local file paths from config object (downloaded by AWS handler).
    
    This creates an embedded PDF ready to be filled later.
    
    Args:
        config: Storage config with local file paths already set
        user_id: User ID (required)
        pdf_doc_id: PDF document ID (required)
        session_id: Optional session ID for tracking
        investor_type: Investor type for mapping (default: 'individual')
        mapping_config: Optional mapping configuration
        use_second_mapper: Whether to use second mapper (default: False)
        notifier: Optional notification system
    """
    start_time = time.time()
    
    logger.info("=" * 80)
    logger.info("MAKE EMBED FILE OPERATION - Partial Pipeline (Extract → Map → Embed)")
    logger.info("=" * 80)
    logger.info(f"User ID: {user_id}, PDF Doc ID: {pdf_doc_id}")
    logger.info(f"Session ID: {session_id}, Investor Type: {investor_type}")
    
    try:
        import json
        import os
        import tempfile
        
        # Store pdf_doc_id on config for structured output paths (if output_base_path is set)
        if hasattr(config, 'output_base_path') and config.output_base_path:
            config.pdf_doc_id = pdf_doc_id
        
        # Get S3 source paths for operations (NOT local paths)
        # Operations will download/upload using these S3 paths
        input_pdf_s3 = config.s3_input_pdf if hasattr(config, 's3_input_pdf') and config.s3_input_pdf else config.local_input_pdf
        input_json_s3 = (config.s3_global_json if hasattr(config, 's3_global_json') and config.s3_global_json 
                        else config.s3_input_json if hasattr(config, 's3_input_json') and config.s3_input_json
                        else getattr(config, 'local_global_json', None) or config.local_input_json)
        
        if not input_pdf_s3:
            raise ValueError("config.s3_input_pdf or local_input_pdf not set")
        if not input_json_s3:
            raise ValueError("config.s3_global_json/s3_input_json or local_input_json not set")
        
        # Debug: Check if we're using S3 paths or local paths
        if not input_pdf_s3.startswith('s3://'):
            logger.info(f"ℹ️  Using LOCAL path for testing: {input_pdf_s3}")
            logger.debug("(Set config.s3_input_pdf when deploying to Lambda)")
        if not input_json_s3.startswith('s3://'):
            logger.info(f"ℹ️  Using LOCAL path for testing: {input_json_s3}")
            logger.debug("(Set config.s3_input_json when deploying to Lambda)")
        
        logger.info(f"Input PDF: {input_pdf_s3}")
        logger.info(f"Input JSON: {input_json_s3}")
        
        storage_type = config.source_type
        logger.info(f"Storage type: {storage_type}")
        
        # For local storage, use pre-configured paths from LocalStorageConfig
        # For cloud storage, we still need file_config for path generation
        if storage_type == 'local':
            # Local deployment: entrypoint already set all paths in config.local_*
            logger.info("Using pre-configured local paths from LocalStorageConfig")
            file_config = None
        elif hasattr(config, 'output_base_path') and config.output_base_path:
            # Cloud deployment: generate structured output paths
            logger.info(f"Using structured output directory: {config.output_base_path}")
            file_config = config.get_complete_file_config(input_pdf_s3, user_id=user_id, session_id=session_id)
        else:
            file_config = None
        
        pipeline_results = {}
        
        # Stage 1: Extract
        logger.info("\n[1/3] Starting EXTRACT stage...")
        
        # Check if entry point already extracted (for hash check)
        if hasattr(config, 'cached_extraction') and config.cached_extraction:
            logger.info("[Cache] ✅ Using cached extraction from entry point (saves ~5s)")
            extract_result = config.cached_extraction
            
            # Save to file using configured path
            if storage_type == 'local' and hasattr(config, 'local_extracted_json'):
                # Local: use pre-configured path
                extracted_json = config.local_extracted_json
                os.makedirs(os.path.dirname(extracted_json), exist_ok=True)
                with open(extracted_json, 'w') as f:
                    json.dump(extract_result.get('extracted_data', {}), f, indent=2)
                extract_result["output_file"] = extracted_json
                logger.info(f"Saved cached extraction to: {extracted_json}")
            elif file_config:
                # Cloud: use generated structured output path
                extracted_json = file_config["extraction_output_path"]
                os.makedirs(os.path.dirname(extracted_json), exist_ok=True)
                with open(extracted_json, 'w') as f:
                    json.dump(extract_result.get('extracted_data', {}), f, indent=2)
                extract_result["output_file"] = extracted_json
                logger.info(f"Saved cached extraction to: {extracted_json}")
            else:
                # Fallback: Create temp file for extraction
                temp_extract = tempfile.NamedTemporaryFile(mode='w', suffix='_extracted.json', delete=False)
                json.dump(extract_result.get('extracted_data', {}), temp_extract, indent=2)
                temp_extract.close()
                extracted_json = temp_extract.name
                extract_result["output_file"] = extracted_json
                logger.info(f"Saved cached extraction to temp: {extracted_json}")
        else:
            # Run full extraction
            extract_result = await handle_extract_operation(
                config=config,  # Pass config instead of file paths
                user_id=user_id,
                session_id=session_id,
                notifier=notifier,
                pdf_doc_id=pdf_doc_id,
                input_json_doc_id=None,
                input_json_path=input_json_s3,  # Still pass for pre-map estimation
                mapping_config=mapping_config
            )
            extracted_json = extract_result["output_file"]
        
        pipeline_results["extract"] = extract_result
        
        # Track original path BEFORE any moving (for caching)
        original_extracted_json = extracted_json
        
        # If using structured output, move file to proper directory (cloud only)
        if file_config and storage_type != 'local':
            expected_path = file_config["extraction"]["extracted_path"]
            if extracted_json != expected_path:
                logger.info(f"Moving extracted file to structured output: {expected_path}")
                os.makedirs(os.path.dirname(expected_path), exist_ok=True)
                shutil.move(extracted_json, expected_path)
                extracted_json = expected_path
                extract_result["output_file"] = expected_path
        
        # Store both S3 and local paths
        if hasattr(config, 's3_extracted_json'):
            config.s3_extracted_json = extracted_json
        logger.info(f"✅ EXTRACT completed: {extracted_json}")
        
        # Get PDF hash from extraction result
        pdf_hash = extract_result.get('pdf_hash')
        if pdf_hash:
            logger.info(f"PDF fingerprint hash for pdf_doc_id={pdf_doc_id}: {pdf_hash[:16]}...")
        else:
            logger.warning(f"PDF hash not available for caching (pdf_doc_id={pdf_doc_id})")
        
        # CHECK HASH CACHE - Skip MAP if we've processed this PDF structure before
        from src.core.config import settings
        from src.utils.hash_cache import check_hash_cache, save_hash_cache, copy_cached_files
        
        pdf_cache_enabled = getattr(settings, 'pdf_cache_enabled', True)
        cache_result = None
        cache_hit = False
        
        # Get cache registry path directly from config.ini
        cache_registry_path = settings.cache_registry_path
        if not cache_registry_path:
            # Fallback to default local path if not configured
            cache_registry_path = os.path.join(settings.data_output_dir, 'cache', 'hash_registry.json')
            logger.debug(f"No cache_registry_path in config, using default: {cache_registry_path}")
        
        # Initialize variables for dual mapper (needed in all code paths)
        semantic_mapping_path = None
        pdf_category = None
        headers_with_fields_path = None
        final_form_fields_path = None
        combined_mapping_path = None
        llm_predictions_path = None
        rag_predictions_path = None
        rag_api_failed = False
        rag_failure_reason = None
        
        # Initialize destination path variables for cache registration
        dest_semantic_mapping = None
        dest_radio_groups = None
        dest_embedded_pdf = None
        
        if pdf_cache_enabled and pdf_hash:
            try:
                logger.info(f"Checking hash cache at: {cache_registry_path}")
                # Ensure cache directory exists (for local paths)
                if not cache_registry_path.startswith(('s3://', 'gs://', 'azure://')):
                    os.makedirs(os.path.dirname(cache_registry_path), exist_ok=True)
                cache_result = await check_hash_cache(pdf_hash, cache_registry_path)
            except Exception as cache_error:
                logger.warning(f"Cache check failed: {cache_error}. Proceeding with normal MAP operation.")
        
        # If CACHE HIT: Use cached files from config (downloaded to /tmp by entry point)
        if cache_result:
            logger.info(f"🎯 CACHE HIT! Skipping MAP stage (saves ~45s + LLM costs)")
            cache_hit = True
            
            try:
                # Check if entry point already downloaded cached files to /tmp
                if config.cached_mapping_json and config.cached_radio_groups:
                    logger.info("[Cache] Using cached files downloaded by entry point:")
                    logger.info(f"   mapping_json: {config.cached_mapping_json}")
                    logger.info(f"   radio_groups: {config.cached_radio_groups}")
                    
                    semantic_mapping_path = config.cached_mapping_json
                    radio_groups = config.cached_radio_groups
                    
                    # Update config paths so embed operation can find them
                    config.local_mapped_json = semantic_mapping_path
                    config.local_radio_json = radio_groups
                    
                    # Check for dual mapper cached files
                    has_headers = config.cached_headers_with_fields is not None
                    has_final_fields = config.cached_final_form_fields is not None
                    
                    if has_headers and has_final_fields:
                        headers_with_fields_path = config.cached_headers_with_fields
                        final_form_fields_path = config.cached_final_form_fields
                        logger.info(f"   headers_with_fields: {headers_with_fields_path}")
                        logger.info(f"   final_form_fields: {final_form_fields_path}")
                else:
                    # Fallback: Copy cached files if entry point didn't download them
                    logger.info("[Cache] Falling back to copy_cached_files (entry point didn't download)")
                    
                    # Determine target directory for copied files
                    if hasattr(config, 'output_base_path') and config.output_base_path and hasattr(config, 'pdf_doc_id'):
                        # Structured output: use mapping subdirectory
                        mapping_dir = os.path.join(
                            config.output_base_path, 
                            "users", 
                            str(user_id), 
                            "pdfs", 
                            str(config.pdf_doc_id), 
                            "mapping"
                        )
                        os.makedirs(mapping_dir, exist_ok=True)
                        target_dir = mapping_dir
                    else:
                        # Default: same directory as extracted_json
                        target_dir = os.path.dirname(extracted_json)
                    
                    logger.info(f"Copying cached files to: {target_dir}")
                    
                    # Copy cached files to current user location
                    copied_files = await copy_cached_files(
                        source_files=cache_result["reference_files"],
                        target_dir=target_dir
                    )
                    
                    # Get cached mapping files
                    semantic_mapping_path = copied_files.get("mapping_json")
                    radio_groups = copied_files.get("radio_groups")
                    
                    # Update config paths so embed operation can find them
                    config.local_mapped_json = semantic_mapping_path
                    config.local_radio_json = radio_groups
                    
                    # Check if this is a dual mapper cache
                    has_headers = "headers_with_fields" in copied_files
                    has_final_fields = "final_form_fields" in copied_files
                    
                    if has_headers and has_final_fields:
                        headers_with_fields_path = copied_files["headers_with_fields"]
                        final_form_fields_path = copied_files["final_form_fields"]
                
                # Check if this is a dual mapper cache
                if use_second_mapper and has_headers and has_final_fields:
                    # Dual mapper cache hit - we have headers but still need to run RAG
                    logger.info("🎯 DUAL MAPPER: Found cached headers, but RAG predictions are ephemeral (not cached)")
                    
                    # Use the paths we already set above (either from config.cached_* or copied_files)
                    # headers_with_fields_path and final_form_fields_path are already set
                    
                    logger.info(f"✅ Using cached headers:")
                    logger.info(f"   headers_with_fields: {headers_with_fields_path}")
                    logger.info(f"   final_form_fields: {final_form_fields_path}")
                    
                    # Get pdf_category if available
                    pdf_category = cache_result.get("pdf_category")
                    if pdf_category:
                        logger.info(f"📋 PDF Category (cached): {pdf_category}")
                    
                    # Save LLM predictions
                    llm_predictions_path = await save_llm_predictions_to_rag_bucket(
                        semantic_mapping_path=semantic_mapping_path,
                        user_id=user_id,
                        pdf_doc_id=pdf_doc_id,
                        session_id=session_id
                    )
                    
                    # Check if RAG API is configured
                    from src.core.config import settings
                    rag_api_url = getattr(settings, 'rag_api_url', None)
                    
                    if not rag_api_url or rag_api_url.strip() == "":
                        # RAG API not configured - use semantic only
                        logger.warning("⚠️  RAG API not configured (rag_api_url is empty)")
                        logger.info("📋 Using cached semantic mapping only (RAG integration disabled)")
                        
                        rag_api_failed = True
                        rag_failure_reason = "RAG API not configured in settings"
                        
                        # Convert cached semantic mapping to Java format
                        mapping_json = await convert_semantic_to_java_format(
                            semantic_mapping_path=semantic_mapping_path,
                            user_id=user_id,
                            pdf_doc_id=pdf_doc_id
                        )
                    else:
                        # Call RAG API (not cached, regenerate)
                        logger.info("📞 Calling RAG API for fresh predictions...")
                        logger.info(f"   RAG API URL: {rag_api_url}")
                        
                        try:
                            rag_predictions_path = await call_rag_api(
                                user_id=user_id,
                                pdf_doc_id=pdf_doc_id,
                                headers_file_path=final_form_fields_path,
                                extracted_json_path=extracted_json,
                                pdf_hash=pdf_hash,
                                session_id=session_id
                            )
                            
                            logger.info(f"✅ RAG predictions received: {rag_predictions_path}")
                            
                            # Combine mappings
                            mapping_json, combined_mapping_path = await combine_mappings(
                                semantic_mapping_path=semantic_mapping_path,
                                rag_predictions_path=rag_predictions_path,
                                user_id=user_id,
                                pdf_doc_id=pdf_doc_id,
                                session_id=session_id
                            )
                            
                            logger.info(f"✅ Combined mapping created from cached semantic + fresh RAG")
                            
                        except Exception as rag_error:
                            logger.error(f"❌ RAG API call failed: {rag_error}")
                            logger.info("Converting cached semantic mapping to Java format...")
                            mapping_json = await convert_semantic_to_java_format(
                                semantic_mapping_path=semantic_mapping_path,
                                user_id=user_id,
                            pdf_doc_id=pdf_doc_id
                        )
                elif use_second_mapper and not has_headers:
                    # Partial cache hit: semantic mapping cached, but headers missing
                    # Need to extract headers fresh and call RAG API
                    logger.info("⚠️ PARTIAL CACHE HIT: Semantic mapping cached, but headers missing")
                    logger.info("📊 Extracting headers fresh, then calling RAG API...")
                    
                    # Save LLM predictions
                    llm_predictions_path = await save_llm_predictions_to_rag_bucket(
                        semantic_mapping_path=semantic_mapping_path,
                        user_id=user_id,
                        pdf_doc_id=pdf_doc_id,
                        session_id=session_id
                    )
                    
                    # Extract headers fresh
                    from src.headers import get_form_fields_points
                    from src.core.config import get_headers_output_config
                    
                    headers_config = get_headers_output_config(input_pdf_s3, user_id, pdf_doc_id)
                    headers_output_path = headers_config["headers_with_fields_path"]
                    final_fields_output_path = headers_config["final_form_fields_path"]
                    
                    headers_with_fields_path = headers_output_path
                    final_form_fields_path = final_fields_output_path
                    
                    headers_result = await get_form_fields_points(
                        extracted_json_path=extracted_json,
                        headers_output_path=headers_output_path,
                        final_fields_output_path=final_fields_output_path
                    )
                    
                    pdf_category = headers_result.get("pdf_category")
                    if pdf_category:
                        logger.info(f"📋 PDF Category: {pdf_category}")
                    
                    # Check if RAG API is configured
                    from src.core.config import settings
                    rag_api_url = getattr(settings, 'rag_api_url', None)
                    
                    if not rag_api_url or rag_api_url.strip() == "":
                        # RAG API not configured - use semantic only
                        logger.warning("⚠️  RAG API not configured (rag_api_url is empty)")
                        logger.info("📋 Using cached semantic mapping only (RAG integration disabled)")
                        
                        rag_api_failed = True
                        rag_failure_reason = "RAG API not configured in settings"
                        
                        # Convert cached semantic mapping to Java format
                        mapping_json = await convert_semantic_to_java_format(
                            semantic_mapping_path=semantic_mapping_path,
                            user_id=user_id,
                            pdf_doc_id=pdf_doc_id
                        )
                    else:
                        # Call RAG API
                        logger.info("📞 Calling RAG API for fresh predictions...")
                        logger.info(f"   RAG API URL: {rag_api_url}")
                        
                        try:
                            rag_predictions_path = await call_rag_api(
                                user_id=user_id,
                                pdf_doc_id=pdf_doc_id,
                                headers_file_path=final_fields_output_path,
                                extracted_json_path=extracted_json,
                                pdf_hash=pdf_hash,
                                session_id=session_id
                            )
                            
                            logger.info(f"✅ RAG predictions received: {rag_predictions_path}")
                            
                            # Combine mappings
                            mapping_json, combined_mapping_path = await combine_mappings(
                                semantic_mapping_path=semantic_mapping_path,
                                rag_predictions_path=rag_predictions_path,
                                user_id=user_id,
                                pdf_doc_id=pdf_doc_id,
                                session_id=session_id
                            )
                        
                            logger.info(f"✅ Combined mapping created from cached semantic + fresh RAG")
                        
                            # Save headers to cache for next time
                            await save_hash_cache(
                                pdf_hash=pdf_hash,
                                cache_registry_path=cache_registry_path,
                                embedded_pdf=None,
                                mapping_json=semantic_mapping_path,
                                radio_groups=radio_groups,
                                user_id=user_id,
                                pdf_doc_id=pdf_doc_id,
                                pdf_category=pdf_category,
                                headers_with_fields=headers_with_fields_path,
                                final_form_fields=final_form_fields_path,
                                rag_predictions=None,
                                combined_mapping=None
                            )
                            logger.info("✅ Updated cache with headers (RAG predictions NOT cached)")
                            
                        except Exception as rag_error:
                            logger.error(f"❌ RAG API call failed: {rag_error}")
                            logger.info("Converting cached semantic mapping to Java format...")
                            mapping_json = await convert_semantic_to_java_format(
                                semantic_mapping_path=semantic_mapping_path,
                                user_id=user_id,
                                pdf_doc_id=pdf_doc_id
                            )
                        
                        # Still save headers to cache even if RAG failed
                        await save_hash_cache(
                            pdf_hash=pdf_hash,
                            cache_registry_path=cache_registry_path,
                            embedded_pdf=None,
                            mapping_json=semantic_mapping_path,
                            radio_groups=radio_groups,
                            user_id=user_id,
                            pdf_doc_id=pdf_doc_id,
                            pdf_category=pdf_category,
                            headers_with_fields=headers_with_fields_path,
                            final_form_fields=final_form_fields_path,
                            rag_predictions=None,
                            combined_mapping=None
                        )
                
                else:
                    # Standard cache hit (semantic mapper only)
                    logger.info("Using cached semantic mapping")
                    logger.info(f"semantic_mapping_path = {semantic_mapping_path}")
                    
                    # Cached file has wrapper format, but save_llm_predictions needs clean format
                    # Convert to Java format first (strips wrapper and converts to array format)
                    logger.info("🔄 Converting cached semantic mapping to Java format...")
                    with open(semantic_mapping_path, 'r') as f:
                        cached_data = json.load(f)
                    
                    # Strip wrapper if present
                    if isinstance(cached_data, dict) and "predictions" in cached_data:
                        cached_mappings = cached_data["predictions"]
                    else:
                        cached_mappings = cached_data
                    
                    # Convert to Java array format and save to same path
                    java_mapping = {}
                    for field_id, mapping_data in cached_mappings.items():
                        if isinstance(mapping_data, dict):
                            field_name = mapping_data.get("predicted_field_name")
                            confidence = mapping_data.get("confidence", 0.0)
                            java_mapping[field_id] = [field_name, "", confidence] if field_name else [None, None, 0]
                        elif isinstance(mapping_data, list) and len(mapping_data) >= 3:
                            field_name = mapping_data[0]
                            confidence = mapping_data[2]
                            java_mapping[field_id] = [field_name, "", confidence] if field_name else [None, None, 0]
                        elif mapping_data is None:
                            java_mapping[field_id] = [None, None, 0]
                        else:
                            java_mapping[field_id] = [None, None, 0]
                    
                    # Overwrite with Java format
                    with open(semantic_mapping_path, 'w') as f:
                        json.dump(java_mapping, f, indent=2, ensure_ascii=False)
                    logger.info(f"✅ Converted cached mapping to Java format ({len(java_mapping)} fields)")
                    
                    # Now save LLM predictions (already in Java format)
                    llm_predictions_path = await save_llm_predictions_to_rag_bucket(
                        semantic_mapping_path=semantic_mapping_path,
                        user_id=user_id,
                        pdf_doc_id=pdf_doc_id,
                        session_id=session_id
                    )
                    logger.info(f"LLM predictions saved to: {llm_predictions_path}")
                    
                    # NOTE: Cached mapping_json is already in Java-compatible format
                    # (it was converted when first saved to cache)
                    # So we DON'T need to convert again - just use it directly
                    logger.info("✅ Using cached mapping (already in Java-compatible format)")
                    mapping_json = semantic_mapping_path  # Already Java-compatible
                
                logger.info(f"✅ Cache files processed. MAP stage skipped.")
                
                # Save cached files to destination storage immediately
                input_handler, output_handler = create_file_handlers(config)
                
                logger.info("💾 Saving cached MAP outputs to destination storage...")
                saved_mapping = output_handler.save_output(mapping_json, 'mapped_json')
                saved_radio = output_handler.save_output(radio_groups, 'radio_json')
                
                if saved_mapping:
                    logger.info(f"✅ Saved cached mapping to: {saved_mapping}")
                if saved_radio:
                    logger.info(f"✅ Saved cached radio groups to: {saved_radio}")
                
                # Create placeholder result for cached MAP stage
                pipeline_results["map"] = {
                    "status": "cache_hit",
                    "execution_time_seconds": 0.0,
                    "mapping_result": {
                        "mapping_path": mapping_json,
                        "radio_groups_path": radio_groups
                    }
                }
                
                # Store S3 paths
                if hasattr(config, 's3_mapped_json'):
                    config.s3_mapped_json = mapping_json
                    config.s3_radio_json = radio_groups
                
            except Exception as copy_error:
                logger.error(f"Failed to process cached files: {copy_error}. Falling back to normal MAP operation.")
                cache_hit = False
                cache_result = None
                mapping_json = None
                radio_groups = None
        
        # Stage 2: Map (only if cache miss)
        if not cache_hit:
            # CACHE MISS: Run MAP stage
            if pdf_hash:
                logger.info(f"📭 CACHE MISS. Running MAP stage...")
            else:
                logger.info("No PDF hash available. Running MAP stage...")
            
            logger.info("\n[2/3] Starting MAP stage...")
            logger.info(f"Use second mapper (RAG) in parallel: {use_second_mapper}")
            
            if use_second_mapper:
                # Run both mappers in parallel: Semantic Mapper + RAG Mapper
                logger.info("🔀 Running DUAL MAPPER mode: Semantic + RAG in parallel...")
                
                # Import here to avoid circular dependency
                from src.headers import get_form_fields_points
                
                # Get header file paths from config
                if storage_type == 'local' and hasattr(config, 'local_headers_with_fields'):
                    # Local: use pre-configured paths from LocalStorageConfig
                    headers_output_path = config.local_headers_with_fields
                    final_fields_output_path = config.local_final_form_fields
                    logger.info(f"Using pre-configured local header paths:")
                    logger.info(f"  headers_with_fields: {headers_output_path}")
                    logger.info(f"  final_form_fields: {final_fields_output_path}")
                elif file_config and "headers" in file_config:
                    # Cloud: use generated structured output paths
                    headers_output_path = file_config["headers"]["headers_with_fields_path"]
                    final_fields_output_path = file_config["headers"]["final_form_fields_path"]
                    logger.info(f"Using header paths from config:")
                    logger.info(f"  headers_with_fields: {headers_output_path}")
                    logger.info(f"  final_form_fields: {final_fields_output_path}")
                else:
                    # Fallback: Config doesn't have header paths (shouldn't happen with new code)
                    raise ValueError("Missing header paths configuration. Entry point must configure paths first.")
                
                # Store paths for caching
                headers_with_fields_path = headers_output_path
                final_form_fields_path = final_fields_output_path
                
                # Run both mappers in parallel
                semantic_task = handle_map_operation(
                    config=config,  # Pass config instead of file paths
                    mapping_config=mapping_config,
                    user_id=user_id,
                    session_id=session_id,
                    notifier=notifier,
                    pdf_doc_id=pdf_doc_id,
                    investor_type=investor_type
                )
                
                rag_task = get_form_fields_points(
                    extracted_json_path=extracted_json,
                    headers_output_path=headers_output_path,
                    final_fields_output_path=final_fields_output_path
                )
                
                # Wait for both to complete
                logger.info("⏳ Waiting for both mappers to complete...")
                map_result, headers_result = await asyncio.gather(semantic_task, rag_task)
                
                logger.info(f"✅ Semantic mapper completed: {map_result['mapping_result']['mapping_path']}")
                logger.info(f"✅ RAG headers completed: {headers_result['outputs']['final_form_fields']}")
                
                # Get semantic mapper outputs
                semantic_mapping_path = map_result["mapping_result"]["mapping_path"]
                radio_groups = map_result["mapping_result"]["radio_groups_path"]
                
                # Extract pdf_category from headers result
                pdf_category = headers_result.get("pdf_category")
                if pdf_category:
                    logger.info(f"📋 PDF Category: {pdf_category}")
                
                # Save LLM predictions for comparison (source-agnostic)
                llm_predictions_path = await save_llm_predictions_to_rag_bucket(
                    semantic_mapping_path=semantic_mapping_path,
                    user_id=user_id,
                    pdf_doc_id=pdf_doc_id,
                    session_id=session_id
                )
                
                # Check if RAG API is configured before calling
                from src.core.config import settings
                rag_api_url = getattr(settings, 'rag_api_url', None)
                
                if not rag_api_url or rag_api_url.strip() == "":
                    # RAG API not configured - skip it gracefully
                    logger.warning("⚠️  RAG API not configured (rag_api_url is empty)")
                    logger.info("📋 Using semantic mapper only (RAG integration disabled)")
                    
                    rag_api_failed = True
                    rag_failure_reason = "RAG API not configured in settings"
                    
                    # Convert semantic mapping to Java format
                    logger.info("🔄 Converting semantic mapping to Java-compatible format...")
                    mapping_json = await convert_semantic_to_java_format(
                        semantic_mapping_path=semantic_mapping_path,
                        user_id=user_id,
                        pdf_doc_id=pdf_doc_id
                    )
                else:
                    # RAG API is configured - try calling it
                    logger.info("📞 Calling RAG API for predictions...")
                    logger.info(f"   RAG API URL: {rag_api_url}")
                    
                    # Try RAG API call, but save headers to cache even if it fails
                    try:
                        rag_predictions_path = await call_rag_api(
                            user_id=user_id,
                            pdf_doc_id=pdf_doc_id,
                            headers_file_path=final_fields_output_path,
                            extracted_json_path=extracted_json,
                            pdf_hash=pdf_hash,
                            session_id=session_id
                        )
                        
                        logger.info(f"✅ RAG predictions received: {rag_predictions_path}")
                        
                        # Combine both mappings - returns (java_mapping, detailed_predictions)
                        logger.info("🔄 Combining semantic + RAG mappings...")
                        mapping_json, combined_mapping_path = await combine_mappings(
                            semantic_mapping_path=semantic_mapping_path,
                            rag_predictions_path=rag_predictions_path,
                            user_id=user_id,
                            pdf_doc_id=pdf_doc_id,
                            session_id=session_id
                        )
                        
                        logger.info(f"✅ Combined mapping created:")
                        logger.info(f"   📋 Java mapping: {mapping_json}")
                        logger.info(f"   📊 Detailed predictions: {combined_mapping_path}")
                        
                    except Exception as rag_error:
                        logger.error(f"❌ RAG API call failed: {rag_error}")
                    logger.info("💾 Saving headers to cache for next attempt (RAG will be retried)")
                    
                    # Track RAG API failure
                    rag_api_failed = True
                    rag_failure_reason = str(rag_error)
                    
                    # Save partial cache with headers but NO RAG predictions or combined mapping
                    # This allows next attempt to skip expensive header extraction
                    await save_hash_cache(
                        pdf_hash=pdf_hash,
                        cache_registry_path=cache_registry_path,
                        embedded_pdf=None,  # DO NOT cache embedded_pdf
                        mapping_json=semantic_mapping_path,
                        radio_groups=radio_groups,
                        user_id=user_id,
                        pdf_doc_id=pdf_doc_id,
                        pdf_category=pdf_category,
                        headers_with_fields=headers_with_fields_path,
                        final_form_fields=final_form_fields_path,  # Cache format file in RAG folder
                        rag_predictions=None,  # DO NOT cache - RAG failed, will retry next time
                        combined_mapping=None  # DO NOT cache - derived/ephemeral
                    )
                    
                    # Convert semantic mapping to Java format
                    logger.info("🔄 Converting semantic mapping to Java-compatible format (RAG failed)...")
                    mapping_json = await convert_semantic_to_java_format(
                        semantic_mapping_path=semantic_mapping_path,
                        user_id=user_id,
                        pdf_doc_id=pdf_doc_id
                    )
                    logger.info("ℹ️ Continuing with Java-compatible semantic mapping (no RAG predictions)")
            
            else:
                # Original flow: Semantic mapper only
                map_result = await handle_map_operation(
                    config=config,  # Pass config instead of file paths
                    mapping_config=mapping_config,
                    user_id=user_id,
                    session_id=session_id,
                    notifier=notifier,
                    pdf_doc_id=pdf_doc_id,
                    investor_type=investor_type
                )
                semantic_mapping_path = map_result["mapping_result"]["mapping_path"]
                radio_groups = map_result["mapping_result"]["radio_groups_path"]
                
                # Extract DESTINATION paths for cache registration (where files were saved)
                dest_semantic_mapping = map_result["mapping_result"].get("dest_mapping_path")
                dest_radio_groups = map_result["mapping_result"].get("dest_radio_groups_path")
                
                # Save LLM predictions (even in single mapper mode, source-agnostic)
                llm_predictions_path = await save_llm_predictions_to_rag_bucket(
                    semantic_mapping_path=semantic_mapping_path,
                    user_id=user_id,
                    pdf_doc_id=pdf_doc_id,
                    session_id=session_id
                )
                
                # Convert semantic mapping to Java format
                logger.info("🔄 Converting semantic mapping to Java-compatible format...")
                mapping_json = await convert_semantic_to_java_format(
                    semantic_mapping_path=semantic_mapping_path,
                    user_id=user_id,
                    pdf_doc_id=pdf_doc_id
                )
        
        # Store map result for pipeline tracking
        pipeline_results["map"] = {
            "mapping_path": mapping_json,
            "radio_groups_path": radio_groups,
            "semantic_mapping_path": semantic_mapping_path,
            "combined_mapping_path": combined_mapping_path,
            "pdf_category": pdf_category,
            "use_second_mapper": use_second_mapper,
            "rag_api_failed": rag_api_failed,
            "rag_failure_reason": rag_failure_reason
        }
        
        # Store S3 paths
        if hasattr(config, 's3_mapped_json'):
            config.s3_mapped_json = mapping_json
            config.s3_radio_json = radio_groups
        
        # Track original paths BEFORE any moving (for caching)
        original_mapping_json = mapping_json
        original_radio_groups = radio_groups
        
        # If using structured output, move files to proper directory (cloud only, local paths already correct)
        if file_config and storage_type != 'local':
            expected_mapping_path = file_config["mapping"]["mapping_path"]
            expected_radio_path = file_config["mapping"]["radio_groups_path"]
            
            if mapping_json != expected_mapping_path:
                logger.info(f"Moving mapping file to structured output: {expected_mapping_path}")
                os.makedirs(os.path.dirname(expected_mapping_path), exist_ok=True)
                shutil.move(mapping_json, expected_mapping_path)
                mapping_json = expected_mapping_path
                pipeline_results["map"]["mapping_path"] = expected_mapping_path
            
            if radio_groups != expected_radio_path:
                logger.info(f"Moving radio groups to structured output: {expected_radio_path}")
                os.makedirs(os.path.dirname(expected_radio_path), exist_ok=True)
                shutil.move(radio_groups, expected_radio_path)
                radio_groups = expected_radio_path
                pipeline_results["map"]["radio_groups_path"] = expected_radio_path
        
        logger.info(f"✅ MAP completed: {mapping_json}")
        
        # Stage 3: Embed
        logger.info("\n[3/3] Starting EMBED stage...")
        embed_result = await handle_embed_operation(
            config=config,  # Pass config instead of file paths
            user_id=user_id,
            session_id=session_id,
            notifier=notifier,
            pdf_doc_id=pdf_doc_id
        )
        pipeline_results["embed"] = embed_result
        embedded_pdf = embed_result["output_file"]
        
        # Extract DESTINATION path for cache registration (where file was saved)
        dest_embedded_pdf = embed_result.get("dest_output_file")
        
        logger.info(f"🔍 DEBUG: Extracted destination paths for cache:")
        logger.info(f"   dest_embedded_pdf: {dest_embedded_pdf}")
        logger.info(f"   dest_semantic_mapping: {dest_semantic_mapping}")
        logger.info(f"   dest_radio_groups: {dest_radio_groups}")
        
        # Track original path BEFORE any moving (for caching)
        original_embedded_pdf = embedded_pdf
        
        # If using structured output, move file to proper directory (cloud only, local paths already correct)
        if file_config and storage_type != 'local':
            expected_embedded_path = file_config["embedding"]["embedded_pdf_path"]
            if embedded_pdf != expected_embedded_path:
                logger.info(f"Moving embedded PDF to structured output: {expected_embedded_path}")
                os.makedirs(os.path.dirname(expected_embedded_path), exist_ok=True)
                shutil.move(embedded_pdf, expected_embedded_path)
                embedded_pdf = expected_embedded_path
                embed_result["output_file"] = expected_embedded_path
        
        # Store S3 path
        if hasattr(config, 's3_embedded_pdf'):
            config.s3_embedded_pdf = embedded_pdf
        logger.info(f"✅ EMBED completed: {embedded_pdf}")
        
        # SAVE TO CACHE if hash is available and cache is enabled
        if pdf_cache_enabled and pdf_hash and not cache_hit:
            try:
                logger.info("💾 Saving results to hash cache for future use...")
                
                # Use DESTINATION paths (where files were actually saved) instead of processing paths
                # This allows cache to work across container restarts and different environments
                cache_embedded = dest_embedded_pdf if dest_embedded_pdf else embedded_pdf
                cache_mapping = dest_semantic_mapping if dest_semantic_mapping else semantic_mapping_path
                cache_radio = dest_radio_groups if dest_radio_groups else radio_groups
                
                logger.info(f"   Cache will reference persistent paths:")
                logger.info(f"      embedded_pdf: {cache_embedded}")
                logger.info(f"      mapping_json: {cache_mapping}")
                logger.info(f"      radio_groups: {cache_radio}")
                
                # IMPORTANT: Save semantic_mapping_path (raw semantic mapper output),
                # NOT mapping_json (Java-converted). Java conversion is done on-demand.
                await save_hash_cache(
                    pdf_hash=pdf_hash,
                    cache_registry_path=cache_registry_path,
                    embedded_pdf=cache_embedded,  # Use destination path
                    mapping_json=cache_mapping,  # Use destination path
                    radio_groups=cache_radio,  # Use destination path
                    user_id=user_id,
                    pdf_doc_id=pdf_doc_id,
                    headers_with_fields=headers_with_fields_path if use_second_mapper else None,
                    final_form_fields=final_form_fields_path if use_second_mapper else None
                )
                logger.info("✅ Results saved to cache successfully")
            except Exception as cache_save_error:
                logger.warning(f"Failed to save to cache: {cache_save_error}. Continuing anyway.")
        
        end_time = time.time()
        total_duration = round(end_time - start_time, 2)
        
        # Get PDF hash from extract result
        pdf_hash = extract_result.get('pdf_hash')
        
        logger.info("\n" + "=" * 80)
        logger.info(f"✅ MAKE EMBED FILE SUCCESS in {total_duration}s")
        logger.info(f"Embedded PDF ready for filling: {embedded_pdf}")
        if pdf_hash:
            logger.info(f"PDF fingerprint hash: {pdf_hash[:16]}...")
        logger.info("=" * 80)
        
        return {
            "operation": "make_embed_file",
            "investor_type": investor_type,
            "inputs": {
                "pdf_doc_id": pdf_doc_id,
                "pdf_s3_path": input_pdf_s3,
                "global_input_json": input_json_s3
            },
            "outputs": {
                "refreshed_pdf": input_pdf_s3,  # Same as input in this flow
                "extracted_json": extracted_json,
                "mapping_json": mapping_json,
                "radio_groups_json": radio_groups,
                "embedded_pdf": embedded_pdf,
                "semantic_mapping_json": semantic_mapping_path,
                "llm_predictions": llm_predictions_path,
                "headers_with_fields": headers_with_fields_path,
                "final_form_fields": final_form_fields_path,
                "rag_predictions": rag_predictions_path,
                "combined_mapping": combined_mapping_path
            },
            "pdf_category": pdf_category,
            "pdf_hash": pdf_hash,
            "cache_hit": cache_hit,
            "dual_mapper_info": {
                "enabled": use_second_mapper,
                "rag_api_failed": rag_api_failed,
                "rag_failure_reason": rag_failure_reason if rag_api_failed else None,
                "mapper_used": "Semantic + RAG" if use_second_mapper and not rag_api_failed else "Semantic only"
            },
            "status": "success",
            "pipeline_results": pipeline_results,
            "timing": {
                "total_pipeline_seconds": total_duration,
                "stage_breakdown": pipeline_results
            },
            "storage_type": storage_type,
            "execution_time_seconds": total_duration
        }
        
    except Exception as e:
        end_time = time.time()
        total_duration = round(end_time - start_time, 2)
        
        logger.error("\n" + "=" * 80)
        logger.error(f"❌ MAKE EMBED FILE FAILED after {total_duration}s: {str(e)}")
        logger.error("=" * 80)
        raise


async def handle_make_form_fields_data_points(
    config: Any,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    pdf_doc_id: Optional[int] = None,
    notifier: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Make form fields data points - extracts form fields and processes headers.
    Uses local file paths from config object.
    
    This is typically used for initial PDF analysis to understand form structure.
    
    Args:
        config: Storage config with local file paths already set
        user_id: Optional user ID
        session_id: Optional session ID
        pdf_doc_id: Optional PDF document ID
        notifier: Optional notification system
        
    Returns:
        Operation result with form fields data
    """
    start_time = time.time()
    
    # Get local PDF from config
    input_pdf = config.local_input_pdf
    if not input_pdf:
        raise ValueError("config.local_input_pdf not set - AWS handler must download PDF first")
    
    storage_type = config.source_type
    
    logger.info("=" * 60)
    logger.info("MAKE FORM FIELDS DATA POINTS OPERATION")
    logger.info("=" * 60)
    logger.info(f"Input PDF: {input_pdf}")
    logger.info(f"Storage type: {storage_type}")
    logger.info("Extracting form fields and analyzing structure...")
    
    try:
        # Extract PDF data (includes form fields and headers)
        extract_result = await handle_extract_operation(
            input_file=input_pdf,
            user_id=user_id,
            session_id=session_id,
            notifier=notifier,
            pdf_doc_id=pdf_doc_id
        )
        
        extracted_json_path = extract_result["output_file"]
        
        # Download extracted JSON to process - use actual filename
        local_extracted = f"/tmp/{os.path.basename(extracted_json_path)}"
        download_from_source(extracted_json_path, local_extracted)
        
        # Load and process the extracted data
        import json
        with open(local_extracted, 'r') as f:
            extracted_data = json.load(f)
        
        # Extract form fields data points
        form_fields = extracted_data.get("fields", [])
        headers = extracted_data.get("headers", [])
        pages = extracted_data.get("pages", [])
        
        # Create analysis
        analysis = {
            "total_fields": len(form_fields),
            "total_headers": len(headers),
            "total_pages": len(pages),
            "field_types": {},
            "field_names": [f.get("name", "") for f in form_fields if isinstance(f, dict)]
        }
        
        # Count field types
        for field in form_fields:
            if isinstance(field, dict):
                field_type = field.get("type", "unknown")
                analysis["field_types"][field_type] = analysis["field_types"].get(field_type, 0) + 1
        
        # Save analysis result
        file_config = get_complete_file_config(input_pdf, user_id, session_id)
        analysis_output_path = file_config["extraction"]["extracted_path"].replace(".json", "_analysis.json")
        
        # Use dynamic filename for analysis
        local_analysis = f"/tmp/{os.path.basename(analysis_output_path)}"
        with open(local_analysis, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        # Upload analysis (works with any storage) - skip if source and dest are the same
        if local_analysis != analysis_output_path:
            upload_to_source(local_analysis, analysis_output_path)
            logger.info(f"Uploaded analysis to: {analysis_output_path}")
        else:
            logger.info(f"Analysis already at destination: {analysis_output_path}")
        
        # Get PDF hash from extract result
        pdf_hash = extract_result.get('pdf_hash')
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        logger.info(f"✅ Form fields analysis completed in {duration}s")
        logger.info(f"   Total fields: {analysis['total_fields']}")
        logger.info(f"   Total headers: {analysis['total_headers']}")
        logger.info(f"   Total pages: {analysis['total_pages']}")
        if pdf_hash:
            logger.info(f"   PDF hash: {pdf_hash[:16]}...")
        logger.info("=" * 60)
        
        return {
            "operation": "make_form_fields_data_points",
            "status": "success",
            "storage_type": storage_type,
            "execution_time_seconds": duration,
            "extracted_json": extracted_json_path,
            "analysis_json": analysis_output_path,
            "analysis": analysis,
            "pdf_hash": pdf_hash  # Include PDF hash
        }
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        logger.error(f"❌ Form fields analysis failed after {duration}s: {str(e)}")
        raise


async def handle_fill_pdf_operation(
    config: Any,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None,
    pdf_doc_id: Optional[int] = None,
    input_json_doc_id: Optional[int] = None,
    notifier: Optional[Any] = None,
    safe_mode: bool = True
) -> Dict[str, Any]:
    """
    Fill PDF operation - fills embedded PDF with data (with optional safety checks).
    Uses local file paths from config object.
    
    This is similar to handle_fill_operation but with additional safety checks.
    
    Args:
        config: Storage config with local file paths already set
        user_id: Optional user ID
        session_id: Optional session ID
        pdf_doc_id: Optional PDF document ID
        input_json_doc_id: Optional input JSON document ID
        notifier: Optional notification system
        safe_mode: If True, checks if embedded PDF exists before filling
        
    Returns:
        Operation result with filled PDF path or error status
    """
    start_time = time.time()
    
    # Get S3 paths from config (for operations to use)
    # Operations will download from S3, process, and upload back to S3
    embedded_pdf_path = config.s3_embedded_pdf if hasattr(config, 's3_embedded_pdf') and config.s3_embedded_pdf else config.local_embedded_pdf
    input_json_path = config.s3_input_json if hasattr(config, 's3_input_json') and config.s3_input_json else config.local_input_json
    
    if not embedded_pdf_path:
        raise ValueError("config.s3_embedded_pdf or local_embedded_pdf not set - must run embed operation first or set manually")
    if not input_json_path:
        raise ValueError("config.s3_input_json or local_input_json not set - AWS handler must download JSON first")
    
    storage_type = config.source_type
    
    logger.info("=" * 60)
    logger.info("FILL PDF OPERATION" + (" (SAFE MODE)" if safe_mode else ""))
    logger.info("=" * 60)
    logger.info(f"Embedded PDF (S3): {embedded_pdf_path}")
    logger.info(f"Input JSON (S3): {input_json_path}")
    logger.info(f"Storage type: {storage_type}")
    
    user_input_details = {
        "user_id": user_id,
        "pdf_doc_id": pdf_doc_id,
        "input_json_doc_id": input_json_doc_id,
        "session_id": session_id
    }
    
    try:
        # Check if embedded PDF exists locally (if in safe mode)
        if safe_mode and hasattr(config, 'local_embedded_pdf'):
            local_embedded = config.local_embedded_pdf
            if local_embedded and not os.path.exists(local_embedded):
                logger.error(f"❌ Embedded PDF not found locally: {local_embedded}")
                return {
                    "operation": "fill_pdf",
                    "status": "error",
                    "error": f"Embedded PDF file not found: {local_embedded}",
                    "pdf_file_path": None,
                    "storage_type": storage_type
                }
        
        # Call the standard fill operation with S3 paths
        fill_result = await handle_fill_operation(
            embedded_pdf_path=embedded_pdf_path,  # Use S3 path
            input_json_path=input_json_path,      # Use S3 path
            user_id=user_id,
            session_id=session_id,
            notifier=notifier,
            pdf_doc_id=pdf_doc_id,
            input_json_doc_id=input_json_doc_id
        )
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        filled_pdf_path = fill_result["output_file"]
        filled_presigned_url = fill_result.get("filled_presigned_url")
        
        logger.info(f"✅ Fill PDF completed in {duration}s")
        logger.info("=" * 60)
        
        # Match original lambda_handler.py return structure
        return {
            "operation": "fill_pdf",
            "inputs": {
                "pdf_doc_id": pdf_doc_id,
                "embedded_pdf": embedded_pdf_path,
                "combined_input_json": input_json_path,
                "user_id": user_id,
                "session_id": session_id,
                "use_profile_info": True  # Default behavior
            },
            "outputs": {
                "filled_pdf": filled_pdf_path,
                "filled_presigned_url": filled_presigned_url
            },
            "status": "success",
            "timing": {
                "total_pipeline_seconds": duration,
                "stage_breakdown": {"fill": duration}
            },
            "storage_type": storage_type,
            "execution_time_seconds": duration
        }
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        if notifier and NOTIFICATIONS_AVAILABLE:
            await safe_notify(
                notifier, "stage_completion",
                stage=PipelineStage.FILL,
                status=StageStatus.FAILED,
                execution_time=duration,
                error_message=str(e),
                level=NotificationLevel.CRITICAL,
                user_input_details=user_input_details
            )
        
        logger.error(f"❌ Fill PDF failed after {duration}s: {str(e)}")
        
        if safe_mode:
            # In safe mode, return error dict instead of raising
            return {
                "operation": "fill_pdf",
                "status": "error",
                "error": str(e),
                "pdf_file_path": None,
                "storage_type": storage_type,
                "execution_time_seconds": duration
            }
        else:
            raise


async def handle_check_embed_file_operation(
    config: Any,
    user_id: Optional[int] = None,
    session_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check embed file operation - verifies if embedded PDF exists.
    Uses local file paths from config object.
    
    This is a lightweight check operation used to verify if an embedded PDF
    is available before attempting to fill it.
    
    Args:
        config: Storage config with local file paths already set
        user_id: Optional user ID
        session_id: Optional session ID
        
    Returns:
        Operation result with existence status and metadata
    """
    start_time = time.time()
    
    # Get local embedded PDF path from config
    embedded_pdf_path = config.local_embedded_pdf
    if not embedded_pdf_path:
        raise ValueError("config.local_embedded_pdf not set - must run embed operation first or set manually")
    
    storage_type = config.source_type
    
    logger.info("=" * 60)
    logger.info("CHECK EMBED FILE OPERATION")
    logger.info("=" * 60)
    logger.info(f"Checking: {embedded_pdf_path}")
    logger.info(f"Storage type: {storage_type}")
    
    try:
        # Check if file exists (local file system check)
        exists = os.path.exists(embedded_pdf_path)
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        if exists:
            logger.info(f"✅ Embedded PDF exists: {embedded_pdf_path}")
            logger.info(f"   Check completed in {duration}s")
            logger.info("=" * 60)
            
            return {
                "operation": "check_embed_file",
                "status": "success",
                "exists": True,
                "embedded_pdf_path": embedded_pdf_path,
                "storage_type": storage_type,
                "message": "Embedded PDF file found and ready for filling",
                "execution_time_seconds": duration
            }
        else:
            logger.warning(f"⚠️  Embedded PDF not found: {embedded_pdf_path}")
            logger.info(f"   Check completed in {duration}s")
            logger.info("=" * 60)
            
            return {
                "operation": "check_embed_file",
                "status": "not_found",
                "exists": False,
                "embedded_pdf_path": embedded_pdf_path,
                "storage_type": storage_type,
                "message": "Embedded PDF file not found. You may need to run make_embed_file operation first.",
                "execution_time_seconds": duration
            }
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        logger.error(f"❌ Check embed file failed after {duration}s: {str(e)}")
        logger.info("=" * 60)
        
        return {
            "operation": "check_embed_file",
            "status": "error",
            "exists": False,
            "embedded_pdf_path": embedded_pdf_path,
            "storage_type": storage_type,
            "error": str(e),
            "message": f"Failed to check embedded PDF: {str(e)}",
            "execution_time_seconds": duration
        }


# ============================================================================
# DUAL MAPPER HELPER FUNCTIONS (RAG Integration)
# ============================================================================

async def call_rag_api(
    user_id: int,
    pdf_doc_id: int,
    headers_file_path: str,
    extracted_json_path: str,
    pdf_hash: str,
    session_id: Optional[str] = None
) -> str:
    """
    Call RAG API to get field predictions based on headers.
    Source-agnostic - works with s3://, gs://, azure://, or local paths.
    
    Args:
        user_id: User ID
        pdf_doc_id: PDF document ID
        headers_file_path: Path to final_form_fields.json (any storage type)
        extracted_json_path: Path to extracted JSON (any storage type)
        pdf_hash: PDF fingerprint hash for caching
        session_id: Optional session ID (will generate if not provided)
        
    Returns:
        Path to rag_predictions.json (same storage type as input)
    """
    import aiohttp
    import uuid
    from src.headers.create_rag_files import create_rag_api_files
    from src.core.config import settings
    
    # Generate session ID if not provided
    if not session_id:
        session_id = f"session_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    logger.info(f"========================================================================")
    
    logger.info(f"Preparing to call RAG API with session_id={session_id}")
    
    try:
        # Create RAG API input files (header_file.json and section_file.json)
        logger.info("Creating RAG API input files from final form fields...")
        
        # NOTE: create_rag_api_files still uses S3Client internally
        # TODO: Refactor create_rag_api_files to be source-agnostic
        from src.clients.s3_client import S3Client
        rag_files = await create_rag_api_files(
            final_form_fields_path=headers_file_path,
            user_id=user_id,
            session_id=session_id,
            pdf_doc_id=pdf_doc_id,
            pdf_hash=pdf_hash,
            s3_client=S3Client()  # Temporary: create_rag_api_files needs refactoring
        )
        
        header_file_path = rag_files["header_file"]
        section_file_path = rag_files["section_file"]
        
        logger.info(f"✅ RAG input files created:")
        logger.info(f"  - header_file: {header_file_path}")
        logger.info(f"  - section_file: {section_file_path}")
        
        # Prepare RAG API request
        rag_api_url = settings.rag_api_url
        rag_api_key = settings.rag_api_key
        
        # NOTE: The RAG API receives S3 paths, not local paths
        # The API is expected to have S3 access to download the files
        # header_file_path is already an S3 path from create_rag_api_files
        payload = {
            "api_name": "get_rag_predictions",
            "user_id": str(user_id),
            "session_id": session_id,
            "pdf_id": str(pdf_doc_id),
            "header_file_location": header_file_path  # S3 path: s3://rag-bucket/.../header_file.json
        }
        
        logger.info(f"Calling RAG API: {rag_api_url}")
        logger.debug(f"RAG API payload: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                rag_api_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": rag_api_key
                },
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"RAG API failed with status {response.status}: {error_text}")
                    raise RuntimeError(f"RAG API returned status {response.status}: {error_text}")
                
                result = await response.json()
                logger.info(f"RAG API response: {result.get('status')}")
                
                # Extract RAG predictions path from response
                if result.get("status") == "success":
                    rag_predictions_path = result["data"]["s3_paths"]["rag_predictions"]
                    logger.info(f"RAG predictions available at: {rag_predictions_path}")
                    return rag_predictions_path
                else:
                    raise RuntimeError(f"RAG API returned error: {result.get('message', 'Unknown error')}")
                    
    except asyncio.TimeoutError:
        logger.error("RAG API call timed out after 5 minutes")
        raise RuntimeError("RAG API call timed out")
    except Exception as e:
        logger.error(f"RAG API call failed: {str(e)}")
        raise RuntimeError(f"Failed to call RAG API: {str(e)}") from e


async def convert_semantic_to_java_format(
    semantic_mapping_path: str,
    user_id: int,
    pdf_doc_id: int
) -> str:
    """
    Convert semantic mapping format to Java-compatible format.
    Source-agnostic - works with s3://, gs://, azure://, or local paths.
    
    CRITICAL: The semantic mapper outputs format: {field_id: [field_name, actual_value, confidence]}
    where actual_value is the data from input JSON (e.g., "553", "John Doe", etc.)
    
    But the Java embedder expects format: {field_id: [field_name, "", confidence]}
    where the middle element MUST be an empty string.
    
    If we pass semantic mapping directly to Java, it tries to parse the actual_value
    as an array and fails with errors like "Not a JSON Array: \"553\"".
    
    This function strips out the actual values and replaces them with empty strings.
    
    Args:
        semantic_mapping_path: Path to semantic mapping file (any storage type)
        user_id: User ID
        pdf_doc_id: PDF document ID
        
    Returns:
        Path to Java-compatible mapping file (same storage type as input)
    """
    logger.info("🔄 Converting semantic mapping to Java-compatible format...")
    logger.info(f"   Input: {semantic_mapping_path}")
    
    # Load semantic mapping
    semantic_temp = f"/tmp/semantic_to_java_{user_id}_{pdf_doc_id}.json"
    download_from_source(semantic_mapping_path, semantic_temp)
    with open(semantic_temp, 'r') as f:
        semantic_data = json.load(f)
    
    # Handle both formats:
    # 1. New format (with predictions wrapper): {"user_id": ..., "predictions": {...}}
    # 2. Old format (direct mappings): {"field_id": [...], ...}
    if isinstance(semantic_data, dict) and "predictions" in semantic_data:
        logger.info("📦 Detected wrapped format with 'predictions' key")
        semantic_mappings = semantic_data["predictions"]
    else:
        logger.info("📋 Detected direct format (no wrapper)")
        semantic_mappings = semantic_data
    
    logger.info(f"📊 Loaded semantic mapping with {len(semantic_mappings)} fields")
    
    # Convert to Java format: replace middle element (actual value) with empty string
    java_mapping = {}
    for field_id, mapping_data in semantic_mappings.items():
        # Handle three possible formats:
        # 1. Array format (old): ["field_name", "actual_value", confidence]
        # 2. Dict format (new): {"predicted_field_name": "...", "confidence": 0.95}
        # 3. Dict format (with value): {"predicted_field_name": "...", "value": "...", "confidence": 0.95}
        
        if isinstance(mapping_data, dict):
            # New dictionary format
            field_name = mapping_data.get("predicted_field_name")
            confidence = mapping_data.get("confidence", 0.0)
            
            if field_name:
                java_mapping[field_id] = [field_name, "", confidence]
            else:
                java_mapping[field_id] = [None, None, 0]
                
        elif isinstance(mapping_data, list) and len(mapping_data) >= 3:
            # Old array format: [field_name, actual_value, confidence]
            # Convert to: [field_name, "", confidence]
            field_name = mapping_data[0]
            confidence = mapping_data[2]
            
            if field_name:
                java_mapping[field_id] = [field_name, "", confidence]
            else:
                java_mapping[field_id] = [None, None, 0]
        else:
            # Fallback for unexpected format
            logger.warning(f"Field {field_id} has unexpected format: {mapping_data}")
            java_mapping[field_id] = [None, None, 0]
    
    logger.info(f"✅ Converted to Java format with {len(java_mapping)} fields")
    
    # Save Java-compatible mapping
    # File name MUST end with _final_mapping_json_combined_java.json for Java embedder
    java_mapping_path = semantic_mapping_path.replace("_mapping.json", "_final_mapping_json_combined_java.json")
    java_mapping_temp = f"/tmp/java_compat_{user_id}_{pdf_doc_id}.json"
    
    with open(java_mapping_temp, 'w') as f:
        json.dump(java_mapping, f, indent=2, ensure_ascii=False)
    
    upload_to_source(java_mapping_temp, java_mapping_path)
    logger.info(f"📤 Java-compatible mapping saved to: {java_mapping_path}")
    logger.info(f"   ✅ Format: {{'field_id': [field_name, '', confidence]}}")
    logger.info(f"   ✅ Middle element is EMPTY STRING (not actual value from input)")
    
    # Verify format
    with open(java_mapping_temp, 'r') as f:
        verify_data = json.load(f)
        sample_keys = list(verify_data.keys())[:3]
        logger.info(f"   ✅ Sample keys: {sample_keys}")
        if "user_id" in verify_data or "final_predictions" in verify_data:
            logger.error(f"   ❌ ERROR: File has wrong structure! Keys: {list(verify_data.keys())[:10]}")
            raise ValueError("Java mapping conversion failed - wrong structure")
        else:
            # Show sample entries
            for key in sample_keys:
                logger.info(f"   ✅ Field {key}: {verify_data[key]}")
    
    return java_mapping_path


async def save_llm_predictions_to_rag_bucket(
    semantic_mapping_path: str,
    user_id: int,
    pdf_doc_id: int,
    session_id: Optional[str] = None
) -> str:
    """
    Save a copy of the semantic mapping (LLM predictions) to the RAG bucket predictions folder.
    Source-agnostic - works with s3://, gs://, azure://, or local paths.
    This allows comparison between LLM and RAG predictions.
    
    Args:
        semantic_mapping_path: Path to semantic mapping JSON (any storage type)
        user_id: User ID
        pdf_doc_id: PDF document ID
        session_id: Session ID for path construction
        
    Returns:
        Path to saved LLM predictions JSON (same storage type as input)
    """
    from datetime import datetime
    from src.core.config import settings
    
    logger.info("📋 Saving LLM predictions to RAG bucket...")
    
    # Download semantic mapping
    semantic_temp = f"/tmp/semantic_mapping_{user_id}_{pdf_doc_id}.json"
    download_from_source(semantic_mapping_path, semantic_temp)
    with open(semantic_temp, 'r') as f:
        semantic_data = json.load(f)
    
    # Create LLM predictions structure (similar to RAG format for easy comparison)
    llm_predictions = {
        "user_id": str(user_id),
        "session_id": session_id or f"session_{int(time.time())}",
        "pdf_id": str(pdf_doc_id),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "source": "llm_semantic_mapper",
        "predictions": {}
    }
    
    # Convert semantic mapping format to predictions format
    for field_id, field_data in semantic_data.items():
        field_key = f"field_{int(field_id)}"
        field_name = field_data[0] if field_data and field_data[0] else None
        confidence = field_data[2] if field_data and len(field_data) > 2 else 0.0
        
        if field_name:
            llm_predictions["predictions"][field_key] = {
                "predicted_field_name": field_name,
                "confidence": confidence
            }
        else:
            llm_predictions["predictions"][field_key] = None
    
    # Save to RAG bucket predictions folder
    storage_type = get_storage_type(semantic_mapping_path)
    if storage_type == "s3":
        rag_bucket = settings.rag_bucket_name
        session_id_final = session_id or llm_predictions["session_id"]
        llm_predictions_key = f"predictions/{user_id}/{session_id_final}/{pdf_doc_id}/predictions/llm_predictions.json"
        llm_predictions_path = f"s3://{rag_bucket}/{llm_predictions_key}"
    else:
        # For non-S3 storage, save alongside semantic mapping
        llm_predictions_path = semantic_mapping_path.replace("_mapping.json", "_llm_predictions.json")
    
    llm_temp = f"/tmp/llm_predictions_{user_id}_{pdf_doc_id}.json"
    with open(llm_temp, 'w') as f:
        json.dump(llm_predictions, f, indent=2, ensure_ascii=False)
    
    upload_to_source(llm_temp, llm_predictions_path)
    logger.info(f"✅ LLM predictions saved to: {llm_predictions_path}")
    logger.info(f"   📊 Total predictions: {len(llm_predictions['predictions'])}")
    
    return llm_predictions_path


async def combine_mappings(
    semantic_mapping_path: str,
    rag_predictions_path: str,
    user_id: int,
    pdf_doc_id: int,
    session_id: Optional[str] = None
) -> tuple:
    """
    Combine semantic mapper output (first phase) with RAG predictions to create final mapping.
    Source-agnostic - works with s3://, gs://, azure://, or local paths.
    
    Strategy:
    - Compare semantic mapping [field_name, null, confidence] with RAG predictions
    - RAG prediction selected if both agree OR RAG has higher confidence
    - Format output as final_predictions with detailed reasoning
    - Save alongside input files with appropriate naming
    
    Args:
        semantic_mapping_path: Path to first phase mapping JSON (any storage type)
        rag_predictions_path: Path to RAG predictions JSON (any storage type)
        user_id: User ID
        pdf_doc_id: PDF document ID
        session_id: Session ID for path construction
        
    Returns:
        Tuple of (java_mapping_path, final_predictions_path):
        - java_mapping_path: Path to Java-compatible mapping for embedder
        - final_predictions_path: Path to detailed predictions with reasoning
    """
    from datetime import datetime
    from src.core.config import settings
    
    logger.info("🔄 Combining semantic mapping with RAG predictions...")
    
    # Load semantic mapping (first phase format: {field_id: [field_name, null, confidence]})
    semantic_temp = f"/tmp/semantic_mapping_{user_id}_{pdf_doc_id}.json"
    download_from_source(semantic_mapping_path, semantic_temp)
    with open(semantic_temp, 'r') as f:
        semantic_data = json.load(f)
    
    # Load RAG predictions (format: {predictions: {field_1: {...}, field_2: null, ...}})
    rag_temp = f"/tmp/rag_predictions_{user_id}_{pdf_doc_id}.json"
    download_from_source(rag_predictions_path, rag_temp)
    with open(rag_temp, 'r') as f:
        rag_data = json.load(f)
    
    rag_predictions = rag_data.get('predictions', {})
    
    logger.info(f"📊 Semantic mapping has {len(semantic_data)} fields")
    logger.info(f"📊 RAG predictions has {len(rag_predictions)} predictions")
    
    # Create final predictions with reasoning
    final_predictions = {}
    stats = {
        "both_agreed_rag_selected": 0,
        "both_agreed_llm_selected": 0,
        "disagreed_rag_selected": 0,
        "disagreed_llm_selected": 0,
        "neither_predicted": 0,
        "only_rag": 0,
        "only_llm": 0
    }
    
    # Get all unique field IDs from both sources
    all_field_ids = set()
    
    # Add semantic field IDs (keys are integers like "1", "2", etc.)
    for fid in semantic_data.keys():
        all_field_ids.add(int(fid))
    
    # Add RAG field IDs (keys are like "field_1", "field_2", etc.)
    for field_key in rag_predictions.keys():
        if field_key.startswith("field_"):
            fid = field_key.replace("field_", "")
            if fid.isdigit():
                all_field_ids.add(int(fid))
    
    logger.info(f"🔍 Processing {len(all_field_ids)} unique fields...")
    
    # Process each field
    for fid in sorted(all_field_ids):
        field_key = f"field_{fid:03d}"  # Format as field_001, field_002, etc.
        
        # Get semantic prediction (format: [field_name, null, confidence])
        semantic_pred = semantic_data.get(str(fid))
        llm_field_name = semantic_pred[0] if semantic_pred and semantic_pred[0] else None
        llm_confidence = semantic_pred[2] if semantic_pred and len(semantic_pred) > 2 else 0.0
        
        # Get RAG prediction
        rag_field_key = f"field_{fid}"
        rag_pred = rag_predictions.get(rag_field_key)
        rag_field_name = None
        rag_confidence = None
        
        if rag_pred and isinstance(rag_pred, dict):
            rag_field_name = rag_pred.get('predicted_field_name')
            rag_confidence = rag_pred.get('confidence')
        
        # Decision logic
        selected_name = None
        selected_from = None
        reason = None
        
        if rag_field_name and llm_field_name:
            # Both predicted
            if rag_field_name == llm_field_name:
                # Both agree
                selected_name = rag_field_name
                selected_from = "rag"
                reason = "Both agreed, RAG selected as primary"
                stats["both_agreed_rag_selected"] += 1
            else:
                # Disagreement - select higher confidence
                if rag_confidence >= llm_confidence:
                    selected_name = rag_field_name
                    selected_from = "rag"
                    reason = f"RAG and LLM disagreed, RAG selected due to higher confidence"
                    stats["disagreed_rag_selected"] += 1
                else:
                    selected_name = llm_field_name
                    selected_from = "llm"
                    reason = f"RAG and LLM disagreed, LLM selected due to higher confidence"
                    stats["disagreed_llm_selected"] += 1
        
        elif rag_field_name:
            # Only RAG predicted
            selected_name = rag_field_name
            selected_from = "rag"
            reason = "Only RAG predicted"
            stats["only_rag"] += 1
        
        elif llm_field_name:
            # Only LLM predicted
            selected_name = llm_field_name
            selected_from = "llm"
            reason = "Only LLM predicted"
            stats["only_llm"] += 1
        
        else:
            # Neither predicted
            reason = "Neither RAG nor LLM predicted"
            stats["neither_predicted"] += 1
        
        # Add to final predictions
        final_predictions[field_key] = {
            "selected_field_name": selected_name,
            "selected_from": selected_from,
            "rag_confidence": rag_confidence,
            "llm_confidence": llm_confidence,
            "reason": reason
        }
    
    # Create final output structure
    final_output = {
        "user_id": str(user_id),
        "session_id": session_id or rag_data.get('session_id', 'unknown'),
        "pdf_id": str(pdf_doc_id),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "pdf_hash": rag_data.get('pdf_hash', ''),
        "final_predictions": final_predictions,
        "summary": {
            "total_fields": len(all_field_ids),
            "predicted_fields": len(all_field_ids) - stats["neither_predicted"],
            "unpredicted_fields": stats["neither_predicted"],
            "both_agreed": stats["both_agreed_rag_selected"],
            "disagreed_rag_won": stats["disagreed_rag_selected"],
            "disagreed_llm_won": stats["disagreed_llm_selected"],
            "only_rag": stats["only_rag"],
            "only_llm": stats["only_llm"]
        }
    }
    
    logger.info(f"✅ Final predictions created:")
    logger.info(f"   Total fields: {final_output['summary']['total_fields']}")
    logger.info(f"   Predicted: {final_output['summary']['predicted_fields']}")
    logger.info(f"   Both agreed: {stats['both_agreed_rag_selected']}")
    logger.info(f"   RAG won disagreement: {stats['disagreed_rag_selected']}")
    logger.info(f"   LLM won disagreement: {stats['disagreed_llm_selected']}")
    
    # Create Java-compatible mapping format [field_name, "", confidence]
    logger.info("📋 Creating Java-compatible mapping format...")
    java_mapping = {}
    
    for fid in sorted(all_field_ids):
        field_key = f"field_{fid:03d}"
        prediction = final_predictions[field_key]
        
        field_name = prediction["selected_field_name"]
        
        # Determine confidence (use the selected source's confidence)
        if prediction["selected_from"] == "rag" and prediction["rag_confidence"]:
            confidence = prediction["rag_confidence"]
        elif prediction["selected_from"] == "llm" and prediction["llm_confidence"]:
            confidence = prediction["llm_confidence"]
        else:
            confidence = 0.0
        
        # Format as [field_name, "", confidence] or [null, null, 0] if not predicted
        if field_name:
            java_mapping[str(fid)] = [field_name, "", round(confidence, 2)]
        else:
            java_mapping[str(fid)] = [None, None, 0]
    
    logger.info(f"✅ Java-compatible mapping created with {len(java_mapping)} fields")
    
    # Save detailed predictions
    storage_type = get_storage_type(semantic_mapping_path)
    session_id_final = session_id or rag_data.get('session_id', f"session_{int(time.time())}")
    
    if storage_type == "s3":
        rag_bucket = settings.rag_bucket_name
        final_predictions_key = f"predictions/{user_id}/{session_id_final}/{pdf_doc_id}/predictions/final_predictions.json"
        final_predictions_path = f"s3://{rag_bucket}/{final_predictions_key}"
    else:
        # For non-S3 storage, save alongside semantic mapping
        final_predictions_path = semantic_mapping_path.replace("_mapping.json", "_final_predictions.json")
    
    final_temp = f"/tmp/final_predictions_{user_id}_{pdf_doc_id}.json"
    with open(final_temp, 'w') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)
    
    upload_to_source(final_temp, final_predictions_path)
    logger.info(f"📤 Final predictions saved to: {final_predictions_path}")
    
    # Save Java-compatible mapping for Java embedder
    # CRITICAL: Java embedder expects simple format {field_id: [name, "", conf]}
    # The file name MUST end with _final_mapping_json_combined_java.json
    java_mapping_path = semantic_mapping_path.replace("_mapping.json", "_final_mapping_json_combined_java.json")
    java_mapping_temp = f"/tmp/java_mapping_{user_id}_{pdf_doc_id}.json"
    
    with open(java_mapping_temp, 'w') as f:
        json.dump(java_mapping, f, indent=2, ensure_ascii=False)
    
    upload_to_source(java_mapping_temp, java_mapping_path)
    logger.info(f"📤 Java-compatible mapping saved to: {java_mapping_path}")
    logger.info(f"   ✅ Format: {{'field_id': [field_name, '', confidence]}}")
    logger.info(f"   ✅ This is the EXACT file Java embedder will receive")
    
    # Verify the file was saved correctly (debug)
    with open(java_mapping_temp, 'r') as f:
        saved_data = json.load(f)
        logger.info(f"   ✅ Verified: File contains {len(saved_data)} field mappings")
        if "user_id" in saved_data or "final_predictions" in saved_data:
            logger.error(f"   ❌ ERROR: Java mapping file contains wrong structure!")
            logger.error(f"   Keys found: {list(saved_data.keys())[:10]}")
            raise ValueError("Java mapping file has wrong structure - contains detailed predictions instead of simple array format")
        else:
            logger.info(f"   ✅ Correct format: Keys are field IDs like '1', '2', '3'...")
            # Show first few entries for verification
            sample_items = list(saved_data.items())[:3]
            for fid, mapping in sample_items:
                logger.info(f"   ✅ Field {fid}: {mapping}")
    
    # Return both the Java mapping (for embedder) and detailed predictions (for output notification)
    logger.info(f"✅ Returning both paths:")
    logger.info(f"   📋 Java mapping: {java_mapping_path}")
    logger.info(f"   📊 Detailed predictions: {final_predictions_path}")
    
    return java_mapping_path, final_predictions_path


