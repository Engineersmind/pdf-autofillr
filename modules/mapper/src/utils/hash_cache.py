"""
PDF Hash Cache Utility

Manages caching of PDF hash -> embedded file mappings in S3.
Enables skipping expensive MAP operation when same PDF structure is encountered.
"""

import json
import time
from typing import Optional, Dict
from src.clients.s3_client import S3Client
import logging
from src.core.config import settings

logger = logging.getLogger(__name__)

# Cache configuration from settings
def get_pdf_cache_bucket() -> str:
    """Get PDF cache bucket from settings, fallback to storage bucket."""
    pdf_cache_bucket = getattr(settings, 'pdf_cache_bucket', '')
    if not pdf_cache_bucket:
        pdf_cache_bucket = getattr(settings, 'storage_s3_bucket', 'your-bucket-name')
    return pdf_cache_bucket

def get_pdf_cache_s3_path() -> str:
    """Get full S3 path to cache file."""
    cache_prefix = getattr(settings, 'pdf_cache_prefix', 'pdf_cache')
    return f"s3://{get_pdf_cache_bucket()}/{cache_prefix}/hash_registry.json"


async def check_hash_cache(
    pdf_hash: str
) -> Optional[Dict]:
    """
    Check if this PDF hash has been processed before.
    
    Args:
        pdf_hash: SHA-256 hash of PDF structure fingerprint
        
    Returns:
        Cache entry dict if found, None otherwise.
        Cache entry contains:
        - reference_files: Dict with embedded_pdf, mapping_json, radio_groups S3 paths
        - usage_count: Number of times this hash has been used
        - created_at: Timestamp when first cached
        - last_used_at: Timestamp when last used
    """
    cache_key = pdf_hash  # Just use hash as key (embedded PDF is same for all investor types)
    
    logger.info(f"Checking hash cache for key: {cache_key[:32]}...")
    
    try:
        # Get cache S3 path
        cache_s3_path = get_pdf_cache_s3_path()
        
        # Download cache file from S3
        s3_client = S3Client()
        
        if not s3_client.object_exists(cache_s3_path):
            logger.info("Cache file does not exist yet. This is the first hash.")
            return None
        
        local_cache_path = "/tmp/hash_cache_registry.json"
        s3_client.download_file_from_s3(cache_s3_path, local_cache_path)
        
        # Load cache data (handle empty file case)
        try:
            with open(local_cache_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    logger.info("Cache file is empty. Treating as cache miss.")
                    return None
                cache_data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"Cache file is corrupted or empty: {e}. Treating as cache miss.")
            return None
        
        entries = cache_data.get('entries', {})
        
        if cache_key not in entries:
            logger.info(f"Cache MISS for key: {cache_key[:32]}...")
            return None
        
        entry = entries[cache_key]
        logger.info(f"Cache HIT for key: {cache_key[:32]}... (usage_count={entry.get('usage_count', 0)})")
        
        # Update usage statistics
        entry['usage_count'] = entry.get('usage_count', 0) + 1
        entry['last_used_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        
        # Save updated cache back to S3 (async - fire and forget style)
        try:
            cache_data['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            with open(local_cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            s3_client.upload_file_to_s3(local_cache_path, cache_s3_path)
            logger.debug("Updated cache usage statistics")
        except Exception as update_error:
            logger.warning(f"Failed to update cache statistics: {update_error}")
        
        return entry
        
    except Exception as e:
        logger.warning(f"Error checking hash cache: {e}. Proceeding without cache.")
        return None


async def save_hash_cache(
    pdf_hash: str,
    embedded_pdf: str,
    mapping_json: str,
    radio_groups: str,
    user_id: int,
    pdf_doc_id: int,
    pdf_category: Optional[Dict] = None,
    rag_predictions: Optional[str] = None,
    combined_mapping: Optional[str] = None,
    headers_with_fields: Optional[str] = None,
    final_form_fields: Optional[str] = None
):
    """
    Save new cache entry after successful MAP + EMBED operations.
    
    Args:
        pdf_hash: SHA-256 hash of PDF structure fingerprint
        embedded_pdf: S3 path to embedded PDF file
        mapping_json: S3 path to semantic mapping JSON file
        radio_groups: S3 path to radio groups JSON file
        user_id: User ID who first processed this PDF
        pdf_doc_id: PDF document ID
        pdf_category: Optional PDF category classification dict
        rag_predictions: Optional S3 path to RAG predictions JSON file (dual mapper)
        combined_mapping: Optional S3 path to combined mapping JSON file (dual mapper)
        headers_with_fields: Optional S3 path to headers_with_fields.json (dual mapper)
        final_form_fields: Optional S3 path to final_form_fields.json (dual mapper)
    """
    cache_key = pdf_hash  # Just use hash as key
    
    logger.info(f"Saving hash cache entry for key: {cache_key[:32]}...")
    
    try:
        # Get cache S3 path
        cache_s3_path = get_pdf_cache_s3_path()
        
        s3_client = S3Client()
        
        # Load existing cache or create new one
        local_cache_path = "/tmp/hash_cache_registry.json"
        
        if s3_client.object_exists(cache_s3_path):
            try:
                s3_client.download_file_from_s3(cache_s3_path, local_cache_path)
                with open(local_cache_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        cache_data = json.loads(content)
                    else:
                        # Empty file - create new cache structure
                        logger.info("Cache file exists but is empty. Creating new cache structure.")
                        cache_data = {
                            "version": "1.0",
                            "last_updated": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            "total_entries": 0,
                            "entries": {}
                        }
            except (json.JSONDecodeError, Exception) as e:
                # Corrupted cache file - start fresh
                logger.warning(f"Cache file is corrupted ({e}). Creating new cache structure.")
                cache_data = {
                    "version": "1.0",
                    "last_updated": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    "total_entries": 0,
                    "entries": {}
                }
        else:
            # Create new cache structure
            logger.info("Cache file does not exist. Creating new cache structure.")
            cache_data = {
                "version": "1.0",
                "last_updated": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "total_entries": 0,
                "entries": {}
            }
        
        entries = cache_data.get('entries', {})
        
        # Check if entry already exists
        if cache_key in entries:
            logger.info(f"Cache entry already exists for key: {cache_key[:32]}... Updating with new mappers if provided.")
            existing_entry = entries[cache_key]
            
            # Update RAG predictions if provided (dual mapper was run later)
            if rag_predictions:
                existing_entry["reference_files"]["rag_predictions"] = rag_predictions
                logger.info("Updated cache entry with RAG predictions")
            
            if combined_mapping:
                existing_entry["reference_files"]["combined_mapping"] = combined_mapping
                logger.info("Updated cache entry with combined mapping")
            
            if headers_with_fields:
                existing_entry["reference_files"]["headers_with_fields"] = headers_with_fields
                logger.info("Updated cache entry with headers_with_fields")
            
            if final_form_fields:
                existing_entry["reference_files"]["final_form_fields"] = final_form_fields
                logger.info("Updated cache entry with final_form_fields")
            
            if pdf_category:
                existing_entry["pdf_category"] = pdf_category
                logger.info("Updated cache entry with pdf_category")
            
            existing_entry["last_used_at"] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        else:
            # Add new entry with human-readable timestamps
            current_time = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
            
            reference_files = {
                "embedded_pdf": embedded_pdf,
                "mapping_json": mapping_json,
                "radio_groups": radio_groups
            }
            
            # Add optional RAG files if provided
            if rag_predictions:
                reference_files["rag_predictions"] = rag_predictions
            
            if combined_mapping:
                reference_files["combined_mapping"] = combined_mapping
            
            # Add optional header files if provided
            if headers_with_fields:
                reference_files["headers_with_fields"] = headers_with_fields
            
            if final_form_fields:
                reference_files["final_form_fields"] = final_form_fields
            
            entries[cache_key] = {
                "pdf_hash": pdf_hash,
                "created_at": current_time,
                "last_used_at": current_time,
                "usage_count": 1,
                "reference_files": reference_files,
                "original_context": {
                    "user_id": user_id,
                    "pdf_doc_id": pdf_doc_id
                }
            }
            
            # Add pdf_category if available
            if pdf_category:
                entries[cache_key]["pdf_category"] = pdf_category
                logger.info(f"Added pdf_category to cache: {pdf_category}")
        
        # Update metadata
        cache_data['entries'] = entries
        cache_data['total_entries'] = len(entries)
        cache_data['last_updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        
        # Save back to S3
        with open(local_cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        s3_client.upload_file_to_s3(local_cache_path, cache_s3_path)
        
        logger.info(f"Successfully saved cache entry. Total entries: {cache_data['total_entries']}")
        
    except Exception as e:
        logger.error(f"Failed to save hash cache: {e}. Pipeline will continue.")


async def copy_cached_files(
    source_files: Dict[str, str],
    target_user_id: int,
    target_pdf_doc_id: int,
    extracted_json_path: str
) -> Dict[str, str]:
    """
    Copy cached S3 files to new location for current user.
    Uses proper naming convention from get_processing_output_config.
    
    Args:
        source_files: Dict with keys: embedded_pdf, mapping_json, radio_groups (S3 paths)
        target_user_id: Target user ID
        target_pdf_doc_id: Target PDF document ID
        extracted_json_path: Path to extracted JSON (used to determine naming pattern)
        
    Returns:
        Dict with new S3 paths for copied files
    """
    logger.info(f"Copying cached files for user_id={target_user_id}, pdf_doc_id={target_pdf_doc_id}")
    
    # Use get_processing_output_config to get proper file paths
    from src.core.config import get_processing_output_config
    
    processing_config = get_processing_output_config(
        extracted_json_path,
        user_id=target_user_id,
        session_id=None  # No session for make_embed_file operation
    )
    
    s3_client = S3Client()
    target_paths = {}
    
    # Map file types to processing_config keys
    file_mapping = {
        "embedded_pdf": None,  # Will be derived from processing config
        "mapping_json": "mapping_path",
        "radio_groups": "radio_groups_path",
        "rag_predictions": None,  # Will be derived (dual mapper)
        "combined_mapping": None,  # Will be derived (dual mapper)
        "headers_with_fields": None,  # Will be derived (dual mapper)
        "final_form_fields": None  # Will be derived (dual mapper)
    }
    
    for file_type, source_path in source_files.items():
        if not source_path:  # Skip if None (e.g., RAG not available)
            continue
            
        try:
            # Get target path from processing config
            if file_type == "embedded_pdf":
                # Embedded PDF path: base_name_user_{user_id}_embedded.pdf
                if extracted_json_path.startswith("s3://"):
                    s3_parts = extracted_json_path.split('/')
                    bucket = s3_parts[2]
                    key_parts = '/'.join(s3_parts[3:])
                    
                    # Remove _extracted.json and get base name
                    if key_parts.endswith('_extracted.json'):
                        base_key = key_parts[:-15]
                    elif key_parts.endswith('.json'):
                        base_key = key_parts[:-5]
                        if base_key.endswith('_extracted'):
                            base_key = base_key[:-10]
                    else:
                        base_key = key_parts.replace('_extracted', '')
                    
                    target_path = f"s3://{bucket}/{base_key}_user_{target_user_id}_embedded.pdf"
                else:
                    # Local path
                    import os
                    base_path = extracted_json_path.replace('_extracted.json', '')
                    target_path = f"{base_path}_user_{target_user_id}_embedded.pdf"
            elif file_type == "rag_predictions":
                # RAG predictions path: base_name_rag_predictions.json
                if extracted_json_path.startswith("s3://"):
                    s3_parts = extracted_json_path.split('/')
                    bucket = s3_parts[2]
                    key_parts = '/'.join(s3_parts[3:])
                    
                    if key_parts.endswith('_extracted.json'):
                        base_key = key_parts[:-15]
                    else:
                        base_key = key_parts.replace('_extracted.json', '')
                    
                    target_path = f"s3://{bucket}/{base_key}_rag_predictions.json"
                else:
                    base_path = extracted_json_path.replace('_extracted.json', '')
                    target_path = f"{base_path}_rag_predictions.json"
            elif file_type == "combined_mapping":
                # Combined mapping path: base_name_final_mapping_json_combined.json
                if extracted_json_path.startswith("s3://"):
                    s3_parts = extracted_json_path.split('/')
                    bucket = s3_parts[2]
                    key_parts = '/'.join(s3_parts[3:])
                    
                    if key_parts.endswith('_extracted.json'):
                        base_key = key_parts[:-15]
                    else:
                        base_key = key_parts.replace('_extracted.json', '')
                    
                    target_path = f"s3://{bucket}/{base_key}_final_mapping_json_combined.json"
                else:
                    base_path = extracted_json_path.replace('_extracted.json', '')
                    target_path = f"{base_path}_final_mapping_json_combined.json"
            elif file_type == "headers_with_fields":
                # Headers with fields path: base_name_headers_with_fields.json
                if extracted_json_path.startswith("s3://"):
                    s3_parts = extracted_json_path.split('/')
                    bucket = s3_parts[2]
                    key_parts = '/'.join(s3_parts[3:])
                    
                    if key_parts.endswith('_extracted.json'):
                        base_key = key_parts[:-15]
                    else:
                        base_key = key_parts.replace('_extracted.json', '')
                    
                    target_path = f"s3://{bucket}/{base_key}_headers_with_fields.json"
                else:
                    base_path = extracted_json_path.replace('_extracted.json', '')
                    target_path = f"{base_path}_headers_with_fields.json"
            elif file_type == "final_form_fields":
                # Final form fields path: base_name_final_form_fields.json
                if extracted_json_path.startswith("s3://"):
                    s3_parts = extracted_json_path.split('/')
                    bucket = s3_parts[2]
                    key_parts = '/'.join(s3_parts[3:])
                    
                    if key_parts.endswith('_extracted.json'):
                        base_key = key_parts[:-15]
                    else:
                        base_key = key_parts.replace('_extracted.json', '')
                    
                    target_path = f"s3://{bucket}/{base_key}_final_form_fields.json"
                else:
                    base_path = extracted_json_path.replace('_extracted.json', '')
                    target_path = f"{base_path}_final_form_fields.json"
            else:
                # Use processing config for mapping and radio_groups
                config_key = file_mapping[file_type]
                target_path = processing_config[config_key]
            
            # Copy S3 object using server-side copy (no download needed!)
            s3_client.copy_object(source_path, target_path)
            target_paths[file_type] = target_path
            
            logger.info(f"Copied {file_type}: {source_path.split('/')[-1]} -> {target_path}")
            
        except Exception as copy_error:
            logger.error(f"Failed to copy {file_type}: {copy_error}")
            raise
    
    logger.info(f"Successfully copied {len(target_paths)} cached files")
    return target_paths


async def get_cache_stats() -> Dict:
    """
    Get cache statistics (for monitoring/debugging).
    
    Returns:
        Dict with cache statistics: total_entries, cache_size_kb, etc.
    """
    try:
        # Get cache S3 path
        cache_s3_path = get_pdf_cache_s3_path()
        
        s3_client = S3Client()
        
        if not s3_client.object_exists(cache_s3_path):
            return {
                "total_entries": 0,
                "cache_exists": False
            }
        
        local_cache_path = "/tmp/hash_cache_registry.json"
        s3_client.download_file_from_s3(cache_s3_path, local_cache_path)
        
        with open(local_cache_path, 'r') as f:
            cache_data = json.load(f)
        
        import os
        cache_size_kb = os.path.getsize(local_cache_path) / 1024
        
        return {
            "total_entries": cache_data.get('total_entries', 0),
            "cache_exists": True,
            "cache_size_kb": round(cache_size_kb, 2),
            "last_updated": cache_data.get('last_updated'),
            "version": cache_data.get('version')
        }
        
    except Exception as e:
        logger.warning(f"Failed to get cache stats: {e}")
        return {
            "total_entries": 0,
            "cache_exists": False,
            "error": str(e)
        }
