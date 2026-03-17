"""
Module for extracting hierarchical headers and form field data points from extracted PDF data.
This module processes extracted JSON to identify document structure (h1, h2, h3, h4 hierarchies)
and associate form fields with their semantic labels.
"""

import json
import time
import re
import asyncio
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.core.logger import setup_logging
from src.core.config import settings
# S3Client imported conditionally where needed (only for AWS mode)
from src.clients.unified_llm_client import UnifiedLLMClient
from src.prompts.renderer import render as render_prompt, build_messages
from src.utils.llm_json import parse_llm_json

# Setup logging
setup_logging()
import logging
logger = logging.getLogger(__name__)


async def get_form_fields_points(
    extracted_json_path: str,
    headers_output_path: str,
    final_fields_output_path: str,
    chunk_size: int = None,
    max_workers: int = None
) -> Dict[str, Any]:
    """
    Extract hierarchical headers and build final form fields with data points.
    
    This function orchestrates the two-step process:
    1. Extract headers with field mappings (headers_with_fields.json)
    2. Build final form fields with complete hierarchy (final_form_fields.json)
    
    Args:
        extracted_json_path: S3 or local path to extracted JSON
        headers_output_path: S3 or local path for headers_with_fields.json output
        final_fields_output_path: S3 or local path for final_form_fields.json output
        chunk_size: Number of pages per chunk (default from config)
        max_workers: Max parallel workers (default from config)
        
    Returns:
        Dictionary with operation results and statistics
        
    Example:
        result = await get_form_fields_points(
            extracted_json_path="s3://bucket/doc_extracted.json",
            headers_output_path="s3://bucket/doc_headers_with_fields.json",
            final_fields_output_path="s3://bucket/doc_final_form_fields.json"
        )
    """
    start_time = time.time()
    
    # Use config defaults if not provided
    if chunk_size is None:
        chunk_size = settings.headers_chunk_size
    if max_workers is None:
        max_workers = settings.headers_max_workers
    
    logger.info("Starting headers and form fields extraction")
    logger.info(f"Extracted JSON: {extracted_json_path}")
    logger.info(f"Chunk size: {chunk_size}, Max workers: {max_workers}")
    
    try:
        # Step 1: Extract headers with fields
        logger.info("Step 1/2: Extracting hierarchical headers with field mappings")
        headers_result = await extract_headers_with_fields(
            extracted_json_path=extracted_json_path,
            output_path=headers_output_path,
            chunk_size=chunk_size,
            max_workers=max_workers
        )
        
        logger.info(f"Headers extraction completed: {len(headers_result['sections'])} sections found")
        
        # Step 2: Build final form fields
        logger.info("Step 2/2: Building final form fields with complete hierarchy")
        final_fields_result = await build_final_form_fields(
            extracted_json_path=extracted_json_path,
            headers_with_fields_path=headers_output_path,
            output_path=final_fields_output_path
        )
        
        logger.info(f"Final form fields built: {len(final_fields_result['fields'])} fields processed")
        
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        
        result = {
            "operation": "get_form_fields_points",
            "status": "success",
            "execution_time_seconds": duration,
            "outputs": {
                "headers_with_fields": headers_output_path,
                "final_form_fields": final_fields_output_path
            },
            "pdf_category": headers_result.get("pdf_category"),  # Add document classification
            "statistics": {
                "total_pages": headers_result.get("total_pages", 0),
                "total_sections": len(headers_result["sections"]),
                "sections_by_level": {
                    "title": headers_result.get("sections_by_level", {}).get("title", 0),
                    "h1": headers_result.get("sections_by_level", {}).get("h1", 0),
                    "h2": headers_result.get("sections_by_level", {}).get("h2", 0),
                    "h3": headers_result.get("sections_by_level", {}).get("h3", 0),
                    "h4": headers_result.get("sections_by_level", {}).get("h4", 0)
                },
                "fields_with_hierarchy": len(final_fields_result["fields"]),
                "processing_time": {
                    "headers_extraction": headers_result.get("execution_time_seconds", 0),
                    "final_fields_building": final_fields_result.get("execution_time_seconds", 0),
                    "total": duration
                }
            },
            "llm_usage": headers_result.get("llm_usage", {})
        }
        
        logger.info(f"Form fields data points extraction completed in {duration} seconds")
        return result
        
    except Exception as e:
        end_time = time.time()
        duration = round(end_time - start_time, 2)
        logger.error(f"Form fields data points extraction failed after {duration} seconds: {str(e)}")
        raise RuntimeError(f"Headers extraction failed: {str(e)}") from e


async def extract_headers_with_fields(
    extracted_json_path: str,
    output_path: str,
    chunk_size: int,
    max_workers: int
) -> Dict[str, Any]:
    """
    Extract hierarchical headers with field ID mappings from extracted JSON.
    
    This is the first step that processes the extracted PDF data to identify:
    - Document title
    - Page-level headings (h1)
    - Section headings (h2)
    - Field labels (h3)
    - Options/sub-labels (h4)
    
    Each heading is associated with form field IDs (fid) where applicable.
    
    Args:
        extracted_json_path: Path to extracted JSON file
        output_path: Path for headers output
        chunk_size: Number of pages to process per chunk
        max_workers: Maximum parallel workers
        
    Returns:
        Dictionary with extraction results and statistics
    """
    start_time = time.time()
    
    logger.info("Loading extracted data...")
    extracted_data = await load_json_from_storage(extracted_json_path)
    
    pages = extracted_data.get('pages', [])
    total_pages = len(pages)
    
    logger.info(f"Preparing {total_pages} pages with field placeholders...")
    prepared_pages = prepare_pages_with_placeholders(pages)
    
    logger.info(f"Processing {total_pages} pages in chunks of {chunk_size}...")
    
    # Create chunks
    chunks = []
    for i in range(0, total_pages, chunk_size):
        chunk_pages = prepared_pages[i:i + chunk_size]
        chunk_num = i // chunk_size + 1
        is_first = (i == 0)
        chunks.append((chunk_pages, chunk_num, is_first))
    
    total_chunks = len(chunks)
    logger.info(f"Created {total_chunks} chunks, processing in parallel with max {max_workers} concurrent workers...")
    
    # Process all chunks in parallel
    # Each process_chunk uses run_in_executor internally for the blocking LLM call
    chunk_tasks = [
        process_chunk(chunk_pages, chunk_num, is_first)
        for chunk_pages, chunk_num, is_first in chunks
    ]
    
    chunk_results = await asyncio.gather(*chunk_tasks)
    
    # Log results
    for result in chunk_results:
        chunk_num = result.get('chunk_num')
        pages = result.get('pages', 'N/A')
        sections_count = len(result.get('sections', []))
        elapsed = result.get('time', 0)
        logger.info(f"Chunk {chunk_num}: {sections_count} sections from pages {pages} ({elapsed:.2f}s)")
    
    # Combine all sections
    all_sections = []
    pdf_category = None  # Extract pdf_category from first chunk
    
    for result in chunk_results:
        all_sections.extend(result.get('sections', []))
        # Capture pdf_category from first chunk only
        if result.get('pdf_category') and pdf_category is None:
            pdf_category = result.get('pdf_category')
    
    # Log pdf_category
    if pdf_category:
        logger.info(f"Document classification: category={pdf_category.get('category')}, sub_category={pdf_category.get('sub_category')}, document_type={pdf_category.get('document_type')}")
    else:
        logger.warning("No document classification extracted from first chunk")
    
    # Calculate statistics
    sections_by_level = {
        "title": sum(1 for s in all_sections if s.get('level') == 'title'),
        "h1": sum(1 for s in all_sections if s.get('level') == 'h1'),
        "h2": sum(1 for s in all_sections if s.get('level') == 'h2'),
        "h3": sum(1 for s in all_sections if s.get('level') == 'h3'),
        "h4": sum(1 for s in all_sections if s.get('level') == 'h4')
    }
    
    total_fields_linked = sum(1 for s in all_sections if s.get('fid') is not None)
    
    # Prepare output data with pdf_category
    output_data = {
        "sections": all_sections
    }
    
    # Add pdf_category if available
    if pdf_category:
        output_data["pdf_category"] = pdf_category
    
    # Save to storage
    await save_json_to_storage(output_data, output_path)
    
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    # Calculate cumulative LLM usage stats from all chunks
    total_chunks = len(chunk_results)
    total_prompt_tokens = sum(r.get('llm_usage', {}).get('prompt_tokens', 0) for r in chunk_results)
    total_completion_tokens = sum(r.get('llm_usage', {}).get('completion_tokens', 0) for r in chunk_results)
    total_tokens = total_prompt_tokens + total_completion_tokens
    total_cost_usd = sum(r.get('llm_usage', {}).get('cost_usd', 0.0) for r in chunk_results)
    
    # Get model name from first chunk if available
    llm_model = chunk_results[0].get('llm_usage', {}).get('model', 'unknown') if chunk_results else 'unknown'
    
    # Calculate average cost per call and per section
    avg_cost_per_call = total_cost_usd / total_chunks if total_chunks > 0 else 0.0
    cost_per_section = total_cost_usd / len(all_sections) if len(all_sections) > 0 else 0.0
    
    # Log cumulative LLM stats
    logger.info("=" * 80)
    logger.info("HEADERS LLM USAGE SUMMARY")
    logger.info(f"Model: {llm_model}")
    logger.info(f"Total Chunks: {total_chunks}")
    logger.info(f"Total Prompt Tokens: {total_prompt_tokens:,}")
    logger.info(f"Total Completion Tokens: {total_completion_tokens:,}")
    logger.info(f"Total Tokens: {total_tokens:,}")
    logger.info(f"Total Cost: ${total_cost_usd:.6f}")
    logger.info(f"Average Cost per Chunk: ${avg_cost_per_call:.6f}")
    logger.info(f"Cost per Section: ${cost_per_section:.6f}")
    logger.info("=" * 80)
    
    result = {
        "sections": all_sections,
        "pdf_category": pdf_category,  # Include in result
        "total_pages": total_pages,
        "sections_by_level": sections_by_level,
        "fields_linked": total_fields_linked,
        "execution_time_seconds": duration,
        "llm_usage": {
            "model": llm_model,
            "total_chunks": total_chunks,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
            "avg_cost_per_chunk": avg_cost_per_call,
            "cost_per_section": cost_per_section
        }
    }
    
    logger.info(f"Headers extraction completed: {len(all_sections)} sections, {total_fields_linked} fields linked")
    return result


async def build_final_form_fields(
    extracted_json_path: str,
    headers_with_fields_path: str,
    output_path: str
) -> Dict[str, Any]:
    """
    Build final form fields with complete hierarchy data.
    
    This is the second step that combines:
    - Original extracted form fields (with bbox, field_type, etc.)
    - Headers hierarchy (title, h1, h2, h3, h4)
    
    to create a comprehensive data structure for each form field.
    
    Args:
        extracted_json_path: Path to extracted JSON
        headers_with_fields_path: Path to headers with fields JSON
        output_path: Path for final output
        
    Returns:
        Dictionary with build results
    """
    start_time = time.time()
    
    logger.info("Loading extracted data and headers...")
    extracted_data = await load_json_from_storage(extracted_json_path)
    headers_data = await load_json_from_storage(headers_with_fields_path)
    
    # Extract sections and pdf_category
    if isinstance(headers_data, dict):
        headers = headers_data.get("sections", [])
        pdf_category = headers_data.get("pdf_category")
    else:
        # Legacy format: just a list of sections
        headers = headers_data
        pdf_category = None
    
    # Build indexes
    fid_to_header, page_to_structural, fid_to_h2_map = build_header_index(headers)
    
    final_fields = []
    
    for page in extracted_data.get("pages", []):
        page_num = page.get("page_number")
        form_fields = page.get("form_fields", [])
        
        structural = page_to_structural.get(page_num, [])
        page_title, page_h1, page_h2_default, page_section_context_default = find_page_hierarchy(page_num, structural)
        
        for field in form_fields:
            fid = field.get("fid")
            field_type = field.get("field_type")
            field_name = field.get("field_name")
            bbox = field.get("bbox")
            gid = field.get("gid")
            
            # Default header values
            h1_text = page_h1
            h2_text = page_h2_default
            section_context = page_section_context_default
            h3_text = None
            h4_text = None
            
            # Get the correct H2 and section_context for this field from the hierarchy map
            if fid in fid_to_h2_map:
                h2_info = fid_to_h2_map[fid]
                h2_text = h2_info.get("h2") or h2_text
                section_context = h2_info.get("section_context") or section_context
                # For H4 fields, set H3 from parent_h3 if not already set
                if h2_info.get("parent_h3") and not h3_text:
                    h3_text = h2_info.get("parent_h3")
            
            # Get H3/H4 from field-linked headers
            header = fid_to_header.get(fid)
            
            if header:
                level = header.get("level")
                text = header.get("text")
                
                if level == "h3":
                    h3_text = text
                elif level == "h4":
                    h4_text = text
                    # If H4 exists but H3 not set, try to get from hierarchy map
                    if not h3_text and fid in fid_to_h2_map:
                        h3_text = fid_to_h2_map[fid].get("parent_h3")
            
            final_entry = {
                "fid": fid,
                "page": page_num,
                "field_name": field_name,
                "field_type": field_type,
                "gid": gid,
                "bbox": bbox,
                "hierarchy": {
                    "title": page_title,
                    "h1": h1_text,
                    "h2": h2_text,
                    "section_context": section_context,  # NEW: Add section context
                    "h3": h3_text,
                    "h4": h4_text
                }
            }
            
            final_fields.append(final_entry)
    
    # Prepare output data
    output_data = {
        "fields": final_fields
    }
    
    # Add pdf_category if available
    if pdf_category:
        output_data["pdf_category"] = pdf_category
    
    # Save to storage
    await save_json_to_storage(output_data, output_path)
    
    end_time = time.time()
    duration = round(end_time - start_time, 2)
    
    logger.info(f"Final form fields built: {len(final_fields)} fields processed in {duration}s")
    
    return {
        "fields": final_fields,
        "pdf_category": pdf_category,
        "execution_time_seconds": duration
    }


# Helper functions

def prepare_pages_with_placeholders(pages: List[dict]) -> List[dict]:
    """
    Convert extracted JSON pages to format with field placeholders embedded in text.
    Merges text_elements with form_fields to create lines with [FIELD_TYPE:ID] tokens.
    """
    prepared_pages = []
    
    for page in pages:
        page_num = page.get('page_number', 1)
        text_elements = page.get('text_elements', [])
        form_fields = page.get('form_fields', [])
        
        # Create a map of form fields by position for quick lookup
        field_map = {}
        for field in form_fields:
            fid = field.get('fid')
            field_type = field.get('field_type', 'UNKNOWN')
            bbox = field.get('bbox', {})
            
            # Store field info
            field_map[fid] = {
                'type': field_type,
                'bbox': bbox,
                'top': bbox.get('top', 0),
                'left': bbox.get('left', 0)
            }
        
        # Build lines with embedded placeholders
        lines = []
        
        for idx, elem in enumerate(text_elements):
            text = elem.get('text', '').strip()
            bbox = elem.get('bbox', {})
            font_size = elem.get('font_size')
            is_bold = elem.get('font_weight', '').lower() == 'bold'
            
            elem_top = bbox.get('top', 0)
            elem_left = bbox.get('left', 0)
            elem_right = bbox.get('right', elem_left + 100)
            
            # Find fields that are spatially near this text element
            # (within 50pt vertically, to the right horizontally)
            nearby_fields = []
            
            for fid, field_info in field_map.items():
                field_top = field_info['top']
                field_left = field_info['left']
                
                # Check if field is on same line (within 15pt vertical) and to the right
                vertical_diff = abs(field_top - elem_top)
                
                if vertical_diff < 15 and field_left >= elem_left and field_left - elem_right < 200:
                    nearby_fields.append({
                        'fid': fid,
                        'type': field_info['type'],
                        'left': field_left,
                        'distance': field_left - elem_right
                    })
            
            # Sort by left position
            nearby_fields.sort(key=lambda x: x['left'])
            
            # Embed field placeholders in text
            if nearby_fields:
                for field in nearby_fields:
                    text += f" [{field['type']}:{field['fid']}]"
            
            # Create line entry
            line = {
                "lid": f"p{page_num}_l{idx + 1}",
                "text": text,
                "bbox": {"left": elem_left, "top": elem_top},
                "font_size": font_size,
                "is_bold": is_bold
            }
            
            lines.append(line)
        
        # Also add standalone fields that weren't matched to text
        matched_fids = set()
        for line in lines:
            # Extract field IDs from placeholders in text
            placeholders = re.findall(r'\[(\w+):(\d+)\]', line['text'])
            for _, fid_str in placeholders:
                matched_fids.add(int(fid_str))
        
        # Add unmatched fields as separate lines
        for fid, field_info in field_map.items():
            if fid not in matched_fids:
                line = {
                    "lid": f"p{page_num}_f{fid}",
                    "text": f"[{field_info['type']}:{fid}]",
                    "bbox": {
                        "left": field_info['bbox'].get('left', 0), 
                        "top": field_info['bbox'].get('top', 0)
                    },
                    "font_size": 10,
                    "is_bold": False
                }
                lines.append(line)
        
        # Sort lines by position (top, then left)
        lines.sort(key=lambda x: (x['bbox']['top'], x['bbox']['left']))
        
        prepared_pages.append({
            "page_number": page_num,
            "lines": lines
        })
    
    return prepared_pages


async def process_chunk(chunk_pages: List[dict], chunk_num: int, is_first: bool) -> Dict[str, Any]:
    """
    Process a chunk of pages to extract headers with LLM.
    
    Uses configured LLM provider (OpenAI or Claude) to extract hierarchical headers
    from pages with embedded field placeholders.
    
    This runs the synchronous LLM call in a thread pool to avoid blocking.
    """
    start_time = time.time()
    
    page_range = f"{chunk_pages[0]['page_number']}-{chunk_pages[-1]['page_number']}"
    logger.info(f"Processing chunk {chunk_num}: pages {page_range}")
    
    # Create prompt
    prompt = create_header_and_field_prompt(chunk_pages, is_first)
    
    # Create UnifiedLLMClient from headers config
    llm_client = UnifiedLLMClient.create_headers_client()

    logger.info(f"LLM client configured - model: {llm_client.model}, temp: {settings.headers_temperature}, max_tokens: {settings.headers_max_tokens}")
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # Prepare messages for LLM
            system_message_content = render_prompt('headers/system_message.j2').strip()

            messages = build_messages(llm_client.model, prompt, system=system_message_content)
            
            # Run the synchronous LLM call in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def call_llm():
                return llm_client.complete(messages)
            
            llm_response = await loop.run_in_executor(None, call_llm)
            
            # Extract response and usage
            response_text = llm_response.content
            usage = llm_response.usage
            
            # Log token usage and cost
            logger.info(
                f"Chunk {chunk_num} LLM call - Tokens: {usage.total_tokens} "
                f"(prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}), "
                f"Cost: ${usage.cost_usd:.6f}"
            )
            
            chunk_sections = parse_llm_json(response_text)
            elapsed_time = time.time() - start_time
            
            # Get LLM usage stats from the response
            usage_stats = {
                'prompt_tokens': usage.prompt_tokens,
                'completion_tokens': usage.completion_tokens,
                'total_tokens': usage.total_tokens,
                'cost_usd': usage.cost_usd,
                'model': usage.model
            }
            
            sections = chunk_sections.get('sections', [])
            pdf_category = chunk_sections.get('pdf_category')  # Extract pdf_category from first chunk
            
            if not sections:
                if attempt < max_retries - 1:
                    logger.warning(f"Chunk {chunk_num}: No sections found, retrying...")
                    time.sleep(1)
                    continue
                else:
                    logger.warning(f"Chunk {chunk_num}: No sections found after retries")
            
            # Log pdf_category if present (first chunk)
            if pdf_category:
                logger.info(f"Chunk {chunk_num} classification: category={pdf_category.get('category')}, sub_category={pdf_category.get('sub_category')}, document_type={pdf_category.get('document_type')}")
            
            logger.info(f"Chunk {chunk_num} completed: {len(sections)} sections found in {elapsed_time:.2f}s")
            
            result = {
                'chunk_num': chunk_num,
                'pages': page_range,
                'sections': sections,
                'input_tokens': usage.prompt_tokens,  # Legacy compatibility
                'output_tokens': usage.completion_tokens,  # Legacy compatibility
                'llm_usage': usage_stats,  # Full LLM usage stats
                'time': elapsed_time
            }
            
            # Add pdf_category only if present (first chunk)
            if pdf_category:
                result['pdf_category'] = pdf_category
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Chunk {chunk_num}: JSON parsing failed: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            if attempt < max_retries - 1:
                logger.info(f"Retrying chunk {chunk_num}...")
                time.sleep(1)
            else:
                return {
                    'chunk_num': chunk_num,
                    'pages': page_range,
                    'sections': [],
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'time': time.time() - start_time,
                    'error': f"JSON parsing failed: {str(e)}"
                }
                
        except Exception as e:
            logger.error(f"Chunk {chunk_num}: Processing failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying chunk {chunk_num}...")
                time.sleep(1)
            else:
                return {
                    'chunk_num': chunk_num,
                    'pages': page_range,
                    'sections': [],
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'time': time.time() - start_time,
                    'error': str(e)
                }
    
    # Should never reach here, but return empty result
    return {
        'chunk_num': chunk_num,
        'pages': page_range,
        'sections': [],
        'input_tokens': 0,
        'output_tokens': 0,
        'time': time.time() - start_time
    }


def create_header_and_field_prompt(pages_data: List[dict], is_first_chunk: bool) -> str:
    """
    Create prompt for header extraction with field placeholder support.
    Rules stay the same; only output format is slimmed to a single fid.
    """
    return render_prompt(
        'headers/extraction_prompt.j2',
        pages_data=pages_data,
        is_first_chunk=is_first_chunk,
    )


def build_header_index(headers: List[dict]) -> tuple:
    """
    Build indexes for efficient header lookup:
    - fid -> header section (for h3/h4 that reference a field)
    - page -> list of structural headings (title/h1/h2 with section_context)
    - Build hierarchy map: fid -> (h2, section_context, parent_h3) to know which H2 and H3 each field belongs to
    """
    fid_to_header = {}
    page_to_structural = {}
    fid_to_h2_map = {}  # NEW: Map fid to its parent H2 and H3
    
    # Track current hierarchy context as we iterate through headers
    current_h2 = None
    current_h2_section_context = None
    current_h3 = None
    current_h3_fid = None  # Track if H3 itself has a fid
    
    for h in headers:
        level = h.get("level")
        page = h.get("page")
        fid = h.get("fid")
        text = h.get("text")
        
        # Index structural headings by page
        if page is not None and level in ("title", "h1", "h2"):
            page_to_structural.setdefault(page, []).append(h)
        
        # Track current H2 context
        if level == "h2":
            current_h2 = text
            current_h2_section_context = h.get("section_context")
            current_h3 = None  # Reset H3 when entering new H2
        
        # Track current H3 context
        if level == "h3":
            current_h3 = text
            current_h3_fid = fid  # H3 might have its own fid (for text fields)
        
        # Map fields to their H2/H3 context
        if fid is not None:
            # Determine the correct H3 for this field
            field_h3 = None
            if level == "h3":
                # This field IS the H3 (text field with direct label)
                field_h3 = text
            elif level == "h4":
                # This is an H4, use the current H3 context
                field_h3 = current_h3
            
            # This field belongs to current H2
            fid_to_h2_map[fid] = {
                "h2": current_h2,
                "section_context": current_h2_section_context,
                "parent_h3": field_h3  # Store the parent H3 for H4 fields
            }
        
        # Index field-linked headings by fid
        if fid is not None and level in ("h3", "h4"):
            fid_to_header[fid] = h
    
    return fid_to_header, page_to_structural, fid_to_h2_map


def find_page_hierarchy(page: int, structural_headings: List[dict]) -> tuple:
    """
    Find title/h1/h2/section_context for a given page from structural headings.
    Returns (title, h1, h2, section_context)
    """
    title = None
    h1 = None
    h2 = None
    section_context = None
    
    for h in structural_headings:
        lvl = h.get("level")
        if lvl == "title" and title is None:
            title = h.get("text")
        elif lvl == "h1" and h1 is None:
            h1 = h.get("text")
        elif lvl == "h2":
            h2 = h.get("text")  # Take last h2 on page
            section_context = h.get("section_context")  # Get section_context from h2
    
    return title, h1, h2, section_context


async def load_json_from_storage(path: str) -> dict:
    """Load JSON from S3 or local storage"""
    if path.startswith("s3://"):
        from src.clients.s3_client import S3Client
        s3_client = S3Client()
        local_temp_path = f"/tmp/headers_temp_{path.split('/')[-1]}"
        s3_client.download_file_from_s3(path, local_temp_path)
        with open(local_temp_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)


async def save_json_to_storage(data: Any, path: str):
    """Save JSON to S3 or local storage"""
    if path.startswith("s3://"):
        from src.clients.s3_client import S3Client
        s3_client = S3Client()
        local_temp_path = f"/tmp/headers_output_{path.split('/')[-1]}"
        with open(local_temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        s3_client.upload_file_to_s3(local_temp_path, path)
        logger.info(f"Saved to S3: {path}")
    else:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved locally: {path}")
