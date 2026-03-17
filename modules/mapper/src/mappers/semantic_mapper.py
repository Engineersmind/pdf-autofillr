import os
import json
import re
import tiktoken
import logging
from src.utils.timing import timing_decorator
import time
from src.chunkers import get_chunker
from src.utils.storage import save_json
from src.groupers.group_by_llm import GroupByLLM
from src.prompts.renderer import render as render_prompt, build_messages
from src.utils.llm_json import parse_llm_json, MappingOutput

import asyncio
from functools import partial
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor()


class SemanticMapper:
    def __init__(self, method_config: dict = None, chunking_section: dict = None, 
                 llm_provider: str = None, confidence_threshold: float = None, 
                 chunking_strategy: str = None):
        """
        Initialize SemanticMapper with either legacy config dicts or modern parameters.
        
        Args:
            method_config: Legacy config dict (deprecated)
            chunking_section: Legacy config dict (deprecated) 
            llm_provider: LLM provider name ("claude", "openai")
            confidence_threshold: Confidence threshold for mappings
            chunking_strategy: Chunking strategy name
        """
        # Import config system
        from src.core.config import settings, get_semantic_mapper_config, get_chunking_config
        
        from src.clients.unified_llm_client import UnifiedLLMClient

        # Handle legacy constructor calls vs new parameter-based calls
        if method_config is not None or chunking_section is not None:
            # Legacy mode - use provided configs
            logger.warning("Using legacy SemanticMapper constructor. Consider updating to parameter-based constructor.")

            if method_config is None:
                method_config = {}
            if chunking_section is None:
                chunking_section = get_chunking_config()

            # Extract values from legacy configs
            llm_name = method_config.get("llm", settings.llm_model)
            self.confidence_threshold = float(method_config.get("confidence_threshold", settings.mapper_method_confidence_threshold))
            self.include_key_variants = method_config.get("include_key_variants", settings.mapper_method_include_key_variants)
            self.include_field_name_variants = method_config.get("include_field_name_variants", settings.mapper_method_include_field_name_variants)
            self.include_description = method_config.get("include_description", settings.mapper_method_include_description)
            self.llm = UnifiedLLMClient(
                model=llm_name,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                timeout=settings.llm_timeout,
                max_retries=settings.llm_max_retries,
            )
        else:
            # Modern mode - use parameters with config defaults
            semantic_config = get_semantic_mapper_config()
            chunking_section = get_chunking_config()

            self.confidence_threshold = confidence_threshold or semantic_config["confidence_threshold"]
            self.include_key_variants = semantic_config["include_key_variants"]
            self.include_field_name_variants = semantic_config["include_field_name_variants"]
            self.include_description = semantic_config["include_description"]
            if llm_provider:
                self.llm = UnifiedLLMClient(
                    model=llm_provider,
                    temperature=settings.llm_temperature,
                    max_tokens=settings.llm_max_tokens,
                    timeout=settings.llm_timeout,
                    max_retries=settings.llm_max_retries,
                )
            else:
                self.llm = UnifiedLLMClient.create_from_settings()

        self.max_threads = settings.llm_max_threads
        logger.info(f"Initialized SemanticMapper with LLM: {self.llm.model}, max_threads: {self.max_threads}")
        logger.info(f"Config - confidence_threshold: {self.confidence_threshold}")

        # Initialize tokenizer
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

        # Setup chunking strategy
        if chunking_strategy:
            # Override strategy if provided as parameter
            strategy = chunking_strategy
        else:
            strategy = chunking_section.get("current_strategy")

        # Map strategy names to actual chunker names
        strategy_name_map = {
            "page": "page",
            "page_based": "page",
            "window": "window", 
            "window_based": "window"
        }
        
        chunker_strategy = strategy_name_map.get(strategy, strategy)

        strategy_config = next(
            (s for s in chunking_section.get("strategies", []) if s.get("name") == strategy),
            {}
        )
        strategy_config["name"] = chunker_strategy
        
        logger.info(f"Using chunking strategy: {strategy} -> {chunker_strategy}")
        logger.debug(f"Chunking config: {strategy_config}")
        
        self.chunker = get_chunker(chunker_strategy, self.tokenizer, **strategy_config)
        
    def prepare_updated_input_data(self, input_data):
        """Only keep list of keys, ignore values."""
        return list(input_data.keys())
    
    def prepare_updated_input_data_with_description(self, input_data) -> dict:
        return {
            key: [info["description"]] 
            for key, info in input_data.items()
            if "description" in info
        }
    
    def flatten_enriched_data(self, enriched: dict) -> dict:
        return {
            key: info["value"]
            for key, info in enriched.items()
            if isinstance(info, dict) and "value" in info
        }


    def remove_duplicate_keys_in_table_columns(self, mapping_data: dict, extracted_data: dict) -> dict:
        """
        Remove duplicate key assignments within the same column of tables.
        If multiple rows in the same column are assigned the same key, set them to null.
        
        Args:
            mapping_data: The mapping dictionary {fid: (key, value, confidence, description)}
            extracted_data: The extracted data with form_fields containing tid, row, col info
            
        Returns:
            Cleaned mapping dictionary with duplicates in same column removed
        """
        logger.info("🔍 Checking for duplicate key assignments in table columns...")
        
        # Build structure: {tid: {col: [(fid, row, key)]}}
        table_columns = {}
        fid_to_info = {}  # Store field info for each fid
        
        # First, collect all form fields and their table info
        for page in extracted_data.get("pages", []):
            for field in page.get("form_fields", []):
                fid = field.get("fid")
                tid = field.get("tid")
                row = field.get("row")
                col = field.get("col")
                
                # Only process table cells with row/col info
                if tid is not None and row is not None and col is not None:
                    fid_to_info[fid] = {
                        "tid": tid,
                        "row": row,
                        "col": col,
                        "field_name": field.get("field_name", "unknown")
                    }
        
        # Build table column structure with mappings
        # mapping_data format: {fid: (key, value, confidence, description)}
        for fid, mapping_tuple in mapping_data.items():
            fid_int = int(fid) if isinstance(fid, str) else fid
            
            # Extract key from tuple
            mapped_key = None
            if isinstance(mapping_tuple, tuple) and len(mapping_tuple) >= 1:
                mapped_key = mapping_tuple[0]  # key is first element
            elif isinstance(mapping_tuple, dict):
                mapped_key = mapping_tuple.get("key")
            else:
                continue  # Skip invalid entries
            
            # Only check non-null mappings
            if fid_int in fid_to_info and mapped_key:
                info = fid_to_info[fid_int]
                tid = info["tid"]
                col = info["col"]
                row = info["row"]
                
                if tid not in table_columns:
                    table_columns[tid] = {}
                if col not in table_columns[tid]:
                    table_columns[tid][col] = []
                
                table_columns[tid][col].append({
                    "fid": fid,
                    "row": row,
                    "key": mapped_key,
                    "field_name": info["field_name"]
                })
        
        # Find and remove duplicates within each column
        cleaned_mapping = mapping_data.copy()
        total_duplicates_removed = 0
        
        for tid, columns in table_columns.items():
            for col, cells in columns.items():
                # Group by key within this column
                key_counts = {}
                for cell in cells:
                    key = cell["key"]
                    if key not in key_counts:
                        key_counts[key] = []
                    key_counts[key].append(cell)
                
                # Find keys that appear multiple times in the same column
                for key, occurrences in key_counts.items():
                    if len(occurrences) > 1:
                        # Sort by row to make logging consistent (ascending)
                        occurrences.sort(key=lambda x: x["row"])
                        
                        # Keep the first occurrence (top row), remove the rest
                        first_occurrence = occurrences[0]
                        duplicates_to_remove = occurrences[1:]
                        
                        # Format duplicate info without nested f-strings
                        duplicate_info = ", ".join([f"Row {occ['row']} (FID {occ['fid']})" for occ in duplicates_to_remove])
                        
                        logger.warning(
                            f"⚠️  Duplicate key '{key}' found in Table {tid}, Column {col} "
                            f"across {len(occurrences)} rows. Keeping Row {first_occurrence['row']} (FID {first_occurrence['fid']}), "
                            f"removing {len(duplicates_to_remove)} duplicate(s): {duplicate_info}"
                        )
                        
                        # Set only the duplicate occurrences to null (skip the first one)
                        # Preserve the tuple structure: (None, value, confidence, description)
                        for occurrence in duplicates_to_remove:
                            fid = occurrence["fid"]
                            
                            # Get the original tuple and replace key with None
                            original_tuple = cleaned_mapping[fid]
                            if isinstance(original_tuple, tuple) and len(original_tuple) >= 3:
                                # (key, value, confidence) -> (None, value, confidence)
                                cleaned_mapping[fid] = (None, original_tuple[1], original_tuple[2])
                            elif isinstance(original_tuple, tuple) and len(original_tuple) >= 1:
                                # Handle shorter tuples
                                cleaned_mapping[fid] = (None,) + original_tuple[1:]
                            else:
                                # Fallback
                                cleaned_mapping[fid] = None
                            
                            total_duplicates_removed += 1
                            logger.info(
                                f"   ❌ Removed duplicate mapping: FID {fid} (Row {occurrence['row']}, "
                                f"Field: {occurrence['field_name']}) → null"
                            )
                        
                        # Log the kept occurrence
                        logger.info(
                            f"   ✅ Kept original mapping: FID {first_occurrence['fid']} (Row {first_occurrence['row']}, "
                            f"Field: {first_occurrence['field_name']}) with key '{key}'"
                        )
        
        if total_duplicates_removed > 0:
            logger.warning(
                f"⚠️  Total duplicate mappings removed: {total_duplicates_removed} "
                f"(across {sum(len(cols) for cols in table_columns.values())} table columns checked)"
            )
        else:
            logger.info("✅ No duplicate key assignments found in table columns")
        
        return cleaned_mapping   



    def prepare_prompt(self, context_text, input_keys, investor_type, fid_start, fid_end, key_variants, field_name_variants):
        return render_prompt(
            "semantic/mapping_prompt.j2",
            context_text=context_text,
            input_keys=input_keys,
            investor_type=investor_type,
            fid_start=fid_start,
            fid_end=fid_end,
            key_variants=key_variants,
            field_name_variants=field_name_variants or {},
            include_description=self.include_description,
        )
    
    def chunk_keys(self, keys, n_chunks):
        chunk_size = max(1, len(keys) // n_chunks)
        for i in range(0, len(keys), chunk_size):
            yield keys[i:i + chunk_size]
    
    def generate_key_descriptions_bulk(self, keys: list, llm) -> dict:
        prompt = render_prompt("semantic/key_descriptions.j2", keys=keys)
        raw_response = llm.complete(prompt)
        return parse_llm_json(raw_response.content)


    async def enrich_input_data_llm(self, flat_json: dict, llm) -> dict:
        keys = list(flat_json.keys())
        num_threads = min(self.max_threads, len(keys)) if keys else 1
        key_batches = list(self.chunk_keys(keys, num_threads))
        semaphore = asyncio.Semaphore(self.max_threads)

        logger.info(f"We are running max threads  on input batches on {num_threads}")
        
        async def process_batch(batch, idx):
            async with semaphore:
                loop = asyncio.get_running_loop()
                descriptions = await loop.run_in_executor(None, self.generate_key_descriptions_bulk, batch, llm)
                return descriptions

        # Launch all batch tasks (they will gate on the semaphore)
        tasks = [
            asyncio.create_task(process_batch(batch, idx))
            for idx, batch in enumerate(key_batches)
        ]
        results = await asyncio.gather(*tasks)

        # Merge output
        descriptions = {}
        for batch_desc in results:
            descriptions.update(batch_desc)

        enriched = {
            key: {"value": value, "description": descriptions.get(key, "undefined")}
            for key, value in flat_json.items()
        }
        return enriched

    
    async def _process_chunk_async(
        self,
        chunk_key: str,
        chunk_info: dict,
        input_data: dict,
        keys_data: dict,
        investor_type: str,
        input_variants: dict,
        field_name_variants_all: dict,
        semaphore
    ):
        # Overall chunk timing
        chunk_start_time = time.time()
        wait_start_time = time.time()
        logger.info(f"[{chunk_key}] Waiting for semaphore... (Available slots: {semaphore._value})")

        async with semaphore:
            wait_time = time.time() - wait_start_time
            processing_start_time = time.time()
            logger.info(f"[{chunk_key}] Started processing after {wait_time:.2f}s wait (Remaining slots: {semaphore._value})")

            context_text = chunk_info["context"]
            start_fid = chunk_info["start_fid"]
            end_fid = chunk_info["end_fid"]
            field_count = end_fid - start_fid + 1 if end_fid >= start_fid else 0

            logger.info(f"[{chunk_key}] Processing {field_count} fields (fid: {start_fid} — {end_fid})")

            result_mapping = {}
            
            # Track timing for different stages
            timing_info = {
                "wait_time": wait_time,
                "field_count": field_count,
                "prompt_prep_time": 0,
                "llm_call_time": 0,
                "parsing_time": 0,
                "total_processing_time": 0
            }

            if not context_text.strip() or start_fid < 0:
                logger.warning(f"[{chunk_key}] Skipping due to empty context or no valid FIDs.")
                return result_mapping

            # STAGE 1: Filter field name variants for this chunk
            prep_start = time.time()
            field_name_variants_fids = {}
            for fid_str, variants in field_name_variants_all.items():
                try:
                    fid = int(fid_str)
                    if start_fid <= fid <= end_fid:
                        field_name_variants_fids[fid_str] = variants
                except ValueError:
                    logger.warning(f"[{chunk_key}] Skipping invalid fid in field variants: {fid_str}")

            # STAGE 2: Prepare prompt
            prompt = self.prepare_prompt(
                context_text, keys_data, investor_type, start_fid, end_fid, input_variants, field_name_variants_fids
            )
            prep_time = time.time() - prep_start
            timing_info["prompt_prep_time"] = prep_time

            input_tokens = len(self.tokenizer.encode(prompt))
            logger.info(f"[{chunk_key}] Prompt prepared in {prep_time:.2f}s, tokens: {input_tokens}")

            try:
                # STAGE 3: Send to LLM
                llm_start = time.time()
                
                # Use UnifiedLLMClient - returns LLMResponse with usage tracking
                messages = build_messages(self.llm.model, prompt)
                llm_response = await asyncio.to_thread(self.llm.complete, messages)
                
                llm_time = time.time() - llm_start
                timing_info["llm_call_time"] = llm_time
                
                # Extract response content and usage
                raw_response = llm_response.content
                usage = llm_response.usage
                
                logger.info(f"[{chunk_key}] LLM call completed in {llm_time:.2f}s")
                logger.info(
                    f"[{chunk_key}] Tokens - Input: {usage.prompt_tokens}, "
                    f"Output: {usage.completion_tokens}, Total: {usage.total_tokens}"
                )
                logger.info(f"[{chunk_key}] Cost: ${usage.cost_usd:.6f}")
                logger.info(
                    f"[{chunk_key}] Processing speed: "
                    f"{usage.prompt_tokens/llm_time:.1f} input tokens/sec, "
                    f"{usage.completion_tokens/llm_time:.1f} output tokens/sec"
                )

                # Log raw response for debugging
                logger.debug(f"[{chunk_key}] Raw LLM response: {raw_response[:200]}..." if len(raw_response) > 200 else f"[{chunk_key}] Raw LLM response: {raw_response}")

                # STAGE 4: Parse and validate LLM JSON
                parse_start = time.time()
                output = MappingOutput.model_validate(parse_llm_json(raw_response))
                parse_time = time.time() - parse_start
                timing_info["parsing_time"] = parse_time

                logger.debug(f"[{chunk_key}] Parsed {len(output)} field mappings in {parse_time:.3f}s")

                for fid, match in output.items():
                    value = input_data.get(match.key) if match.key else None
                    result_mapping[fid] = (match.key, value, match.con)
                    logger.debug(f"[{chunk_key}] Mapped fid {fid} -> key: {match.key}, confidence: {match.con}")

            except json.JSONDecodeError as e:
                logger.warning(f"[{chunk_key}] Failed to parse LLM JSON response: {e}")
                logger.debug(f"[{chunk_key}] Raw response that failed to parse: {raw_response}")
            except Exception as e:
                logger.error(f"[{chunk_key}] Unexpected error during LLM processing: {e}")

            # Calculate final timing
            processing_time = time.time() - processing_start_time
            total_chunk_time = time.time() - chunk_start_time
            timing_info["total_processing_time"] = processing_time
            
            # Log comprehensive timing breakdown
            logger.info(f"[{chunk_key}] 🕐 Timing Breakdown:")
            logger.info(f"[{chunk_key}]   Wait time: {timing_info['wait_time']:.2f}s")
            logger.info(f"[{chunk_key}]   Prompt prep: {timing_info['prompt_prep_time']:.2f}s")
            logger.info(f"[{chunk_key}]   LLM call: {timing_info['llm_call_time']:.2f}s")
            logger.info(f"[{chunk_key}]   JSON parsing: {timing_info['parsing_time']:.3f}s")
            logger.info(f"[{chunk_key}]   Total processing: {processing_time:.2f}s")
            logger.info(f"[{chunk_key}]   Total chunk time: {total_chunk_time:.2f}s")
            logger.info(f"[{chunk_key}]   Fields/sec: {field_count/processing_time:.1f}")
            logger.info(f"[{chunk_key}] ✅ Completed {field_count} fields, {len(result_mapping)} mappings (Slots now: {semaphore._value})")

            return result_mapping


    @timing_decorator
    async def process_and_save(self, extracted_path, input_json_path, original_pdf_path, storage_config: dict, investor_type: str = None,
                        input_key_json_variants_path: str = None, field_names_json_variants_path: str = None):
        """
        Process semantic mapping and save results
        
        Args:
            extracted_path: Path to extracted JSON
            input_json_path: Path to input keys JSON
            original_pdf_path: Path to original PDF
            storage_config: Storage configuration
            input_key_json_variants_path: Optional key variants
            field_names_json_variants_path: Optional field name variants
            
        Returns:
            dict: Mapping results with timing
            
        Raises:
            ValueError: If required paths are empty or invalid
            FileNotFoundError: If required files don't exist
            RuntimeError: If mapping fails
        """
        # Validate inputs
        if not extracted_path:
            raise ValueError("extracted_path cannot be empty")
        if not input_json_path:
            raise ValueError("input_json_path cannot be empty")
        if not storage_config:
            raise ValueError("storage_config cannot be empty")
        
        process_start_time = time.time()
        mapping_path = storage_config.get("output_path")
        radio_path = storage_config.get("radio_groups")
        
        if not mapping_path:
            raise ValueError("storage_config must contain 'output_path'")
        if not radio_path:
            raise ValueError("storage_config must contain 'radio_groups'")

        logger.info(f"🚀 Starting Field Mapping for: {extracted_path}")
        
        # Track timing for different stages
        stage_timings = {
            "data_loading": 0,
            "key_enrichment": 0,
            "chunking": 0,
            "radio_grouping": 0,
            "chunk_processing": 0,
            "result_saving": 0
        }

        try:
            # STAGE 1: Load data files
            load_start = time.time()
            logger.info("📂 Loading data files...")
            
            try:
                # Load extracted data from local file
                if not os.path.exists(extracted_path):
                    raise FileNotFoundError(f"Extracted JSON not found: {extracted_path}")
                with open(extracted_path, "r", encoding="utf-8") as f:
                    extracted_data = json.load(f)
                
                if not extracted_data or "pages" not in extracted_data:
                    raise ValueError(f"Invalid extracted data format in: {extracted_path}")
                
                # Load input keys from local file
                if not os.path.exists(input_json_path):
                    raise FileNotFoundError(f"Input keys JSON not found: {input_json_path}")
                with open(input_json_path, "r", encoding="utf-8") as f:
                    input_data = json.load(f)
                
                if not input_data:
                    raise ValueError(f"Input keys JSON is empty: {input_json_path}")
                        
                load_time = time.time() - load_start
                stage_timings["data_loading"] = load_time
                logger.info(f"📂 Data loading completed in {load_time:.2f}s")
                
            except (FileNotFoundError, ValueError):
                raise
            except Exception as e:
                logger.error(f"Failed to load data files: {str(e)}", exc_info=True)
                raise RuntimeError(f"Data loading failed: {str(e)}") from e

            # Load optional variants from local files
            input_variants = {}
            if self.include_key_variants and input_key_json_variants_path:
                try:
                    if os.path.exists(input_key_json_variants_path):
                        with open(input_key_json_variants_path, "r", encoding="utf-8") as vf:
                            input_variants = json.load(vf)
                except Exception as e:
                    logger.warning(f"Could not load key variants: {e}")

            field_name_variants_all = {}
            if self.include_field_name_variants and field_names_json_variants_path:
                try:
                    if os.path.exists(field_names_json_variants_path):
                        with open(field_names_json_variants_path, "r", encoding="utf-8") as fvf:
                            field_name_variants_all = json.load(fvf)
                except Exception as e:
                    logger.warning(f"Could not load field name variants: {e}")

            # STAGE 2: Prepare keys and enrichment
            try:
                enrich_start = time.time()
                keys_data = self.prepare_updated_input_data(input_data)
                
                if self.include_description == 1:
                    logger.info("🔧 Preparing & Including key descriptions in the prompt...")
                    enriched_data = await self.enrich_input_data_llm(input_data, llm=self.llm)
                    keys_data = self.prepare_updated_input_data_with_description(enriched_data)
                
                enrich_time = time.time() - enrich_start
                stage_timings["key_enrichment"] = enrich_time
                logger.info(f"🔧 Key enrichment completed in {enrich_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Key enrichment failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Key enrichment failed: {str(e)}") from e

            # STAGE 3: Generate chunks
            try:
                chunk_start = time.time()
                logger.info("📄 Generating context chunks...")
                context_dict, _ = self.chunker.generate_context_and_stats(extracted_data)
                chunk_time = time.time() - chunk_start
                stage_timings["chunking"] = chunk_time
                logger.info(f"📄 Chunking completed in {chunk_time:.2f}s - Generated {len(context_dict)} chunks")
                
                if not context_dict:
                    raise ValueError("No chunks generated from extracted data")
                
            except Exception as e:
                logger.error(f"Chunking failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Context chunking failed: {str(e)}") from e
            
            final_flat_mapping = {}

            # STAGE 4: Radio button grouping
            try:
                radio_start = time.time()
                logger.info("🔘 Processing radio button groups...")
                
                groupby_kwargs = {
                    "llm": self.llm,
                    "field_type": "RADIOBUTTON",
                    "threshold": 2,
                    "keys_data": keys_data,
                }
                
                # Execute radio grouping
                grouper = GroupByLLM(extracted_data, **groupby_kwargs)
                radio_groups_result = grouper.group()
                
                # Extract just the groups (without llm_usage metadata)
                radio_groups = radio_groups_result.get("groups", {})
                
                # Log LLM usage stats for radio grouping
                if "llm_usage" in radio_groups_result:
                    usage = radio_groups_result["llm_usage"]
                    logger.info(
                        f"🔘 Radio grouping LLM usage - Model: {usage.get('model')}, "
                        f"Calls: {usage.get('total_calls')}, "
                        f"Tokens: {usage.get('total_tokens')}, "
                        f"Cost: ${usage.get('total_cost_usd', 0):.6f}"
                    )
                
                # Save radio groups using local storage (only the groups, no metadata)
                radio_storage_config = {
                    "type": "local",
                    "path": radio_path
                }
                save_json(radio_groups, radio_storage_config)
                # Store local path for operations to reference
                local_radio_path = radio_path
                
                radio_time = time.time() - radio_start
                stage_timings["radio_grouping"] = radio_time
                logger.info(f"🔘 Radio grouping completed in {radio_time:.2f}s - Found {len(radio_groups)} groups")
                
            except Exception as e:
                logger.error(f"Radio grouping failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Radio button grouping failed: {str(e)}") from e

            # STAGE 5: Process chunks async
            try:
                processing_start = time.time()
                semaphore = asyncio.Semaphore(self.max_threads)

                logger.info(f"🧠 Starting async processing with {self.max_threads} max threads for {len(context_dict)} chunks...")

                async def run_all_chunks():
                    tasks = []
                    for i, (chunk_key, chunk_info) in enumerate(context_dict.items()):
                        task = self._process_chunk_async(
                            chunk_key, chunk_info,
                            input_data, keys_data, investor_type,
                            input_variants,
                            field_name_variants_all,
                            semaphore
                        )
                        tasks.append(task)
                    results = await asyncio.gather(*tasks)
                    for chunk_result in results:
                        final_flat_mapping.update(chunk_result)

                await run_all_chunks()
                
                processing_time = time.time() - processing_start
                stage_timings["chunk_processing"] = processing_time
                logger.info(f"🧠 Chunk processing completed in {processing_time:.2f}s - Processed {len(final_flat_mapping)} field mappings")
                
                if not final_flat_mapping:
                    logger.warning("No field mappings generated from chunk processing")
                    
            except Exception as e:
                logger.error(f"Chunk processing failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Field mapping chunk processing failed: {str(e)}") from e
            

            try:
                logger.info("🧹 Cleaning duplicate key assignments in table columns...")
                final_flat_mapping = self.remove_duplicate_keys_in_table_columns(
                    final_flat_mapping, 
                    extracted_data
                )
                logger.info("✅ Duplicate key cleaning completed")
            except Exception as e:
                logger.warning(f"Failed to clean duplicate keys in table columns: {str(e)}")
                # Don't fail the entire process, just log and continue

            # STAGE 6: Save results
            try:
                save_start = time.time()
                logger.info("💾 Saving results...")
                
                # Use local storage for saving the mapping
                mapping_storage = storage_config.get("mapping_storage", {
                    "type": "local",
                    "path": storage_config.get("output_path")
                })
                save_json(final_flat_mapping, mapping_storage)
                # Store local path for operations to reference
                local_mapping_path = mapping_storage.get("path")
                
                save_time = time.time() - save_start
                stage_timings["result_saving"] = save_time
                logger.info(f"💾 Results saved in {save_time:.2f}s")
                
            except Exception as e:
                logger.error(f"Result saving failed: {str(e)}", exc_info=True)
                raise RuntimeError(f"Failed to save mapping results: {str(e)}") from e
            
            # Calculate total time and performance metrics
            total_time = time.time() - process_start_time
            total_fields_mapped = len(final_flat_mapping)
            
            # Calculate field statistics from extracted data
            total_fields_in_pdf = 0
            field_type_counts = {}
            for page in extracted_data.get("pages", []):
                for field in page.get("fields", []):
                    total_fields_in_pdf += 1
                    field_type = field.get("field_type", "UNKNOWN")
                    field_type_counts[field_type] = field_type_counts.get(field_type, 0) + 1
            
            # Calculate mapping statistics by type and confidence
            mapped_by_type = {}
            high_confidence_count = 0
            low_confidence_count = 0
            
            for fid, mapping_info in final_flat_mapping.items():
                # mapping_info is a tuple: (key, value, confidence)
                # Get field type from extracted data
                field_type = "UNKNOWN"
                for page in extracted_data.get("pages", []):
                    for field in page.get("fields", []):
                        if str(field.get("fid")) == str(fid):
                            field_type = field.get("field_type", "UNKNOWN")
                            break
                
                mapped_by_type[field_type] = mapped_by_type.get(field_type, 0) + 1
                
                # Count confidence levels - mapping_info is tuple (key, value, confidence)
                if isinstance(mapping_info, tuple) and len(mapping_info) >= 3:
                    confidence = mapping_info[2]  # confidence is 3rd element
                elif isinstance(mapping_info, dict):
                    confidence = mapping_info.get("confidence", 0)
                else:
                    confidence = 0
                    
                if confidence >= 0.8:
                    high_confidence_count += 1
                else:
                    low_confidence_count += 1
            
            logger.info(f"")
            logger.info(f"🎯 SEMANTIC MAPPING COMPLETE!")
            logger.info(f"📊 Field Statistics:")
            logger.info(f"   📄 Total fields in PDF: {total_fields_in_pdf}")
            
            # Log fields by type in extracted data
            for field_type, count in sorted(field_type_counts.items()):
                mapped_count = mapped_by_type.get(field_type, 0)
                percentage = (mapped_count / count * 100) if count > 0 else 0
                logger.info(f"      • {field_type}: {count} total, {mapped_count} mapped ({percentage:.1f}%)")
            
            # Calculate percentages safely (avoid division by zero)
            mapping_percentage = (total_fields_mapped/total_fields_in_pdf*100) if total_fields_in_pdf > 0 else 0
            high_conf_percentage = (high_confidence_count/total_fields_mapped*100) if total_fields_mapped > 0 else 0
            low_conf_percentage = (low_confidence_count/total_fields_mapped*100) if total_fields_mapped > 0 else 0
            
            logger.info(f"   ✅ Total fields mapped: {total_fields_mapped} ({mapping_percentage:.1f}%)")
            logger.info(f"   🎯 High confidence (≥0.8): {high_confidence_count} ({high_conf_percentage:.1f}%)")
            logger.info(f"   ⚠️  Low confidence (<0.8): {low_confidence_count} ({low_conf_percentage:.1f}%)")
            
            logger.info(f"📊 Performance Summary:")
            logger.info(f"   📂 Data loading: {stage_timings['data_loading']:.2f}s ({stage_timings['data_loading']/total_time*100:.1f}%)")
            logger.info(f"   🔧 Key enrichment: {stage_timings['key_enrichment']:.2f}s ({stage_timings['key_enrichment']/total_time*100:.1f}%)")
            logger.info(f"   📄 Chunking: {stage_timings['chunking']:.2f}s ({stage_timings['chunking']/total_time*100:.1f}%)")
            logger.info(f"   🔘 Radio grouping: {stage_timings['radio_grouping']:.2f}s ({stage_timings['radio_grouping']/total_time*100:.1f}%)")
            logger.info(f"   🧠 Chunk processing: {stage_timings['chunk_processing']:.2f}s ({stage_timings['chunk_processing']/total_time*100:.1f}%)")
            logger.info(f"   💾 Result saving: {stage_timings['result_saving']:.2f}s ({stage_timings['result_saving']/total_time*100:.1f}%)")
            logger.info(f"   🕐 Total time: {total_time:.2f}s")
            
            # Calculate processing rate safely
            processing_rate = (total_fields_mapped/total_time) if total_time > 0 else 0
            logger.info(f"   ⚡ Processing rate: {processing_rate:.1f} fields/sec")
            logger.info(f"   📄 Chunks processed: {len(context_dict)}")
            logger.info(f"   🧵 Max threads used: {self.max_threads}")
            logger.info(f"   📁 Output: {mapping_path}")
            
            # Log LLM usage statistics
            llm_stats = self.llm.get_cumulative_stats()
            logger.info(f"")
            logger.info(f"💰 LLM USAGE STATISTICS:")
            logger.info(f"   🤖 Model: {llm_stats['model']}")
            logger.info(f"   📞 Total LLM calls: {llm_stats['total_calls']}")
            logger.info(f"   📊 Tokens - Prompt: {llm_stats['total_prompt_tokens']:,}, Completion: {llm_stats['total_completion_tokens']:,}, Total: {llm_stats['total_tokens']:,}")
            logger.info(f"   💵 Total cost: ${llm_stats['total_cost_usd']:.6f}")
            if llm_stats['total_calls'] > 0:
                logger.info(f"   💰 Avg cost per call: ${llm_stats['total_cost_usd']/llm_stats['total_calls']:.6f}")
            if total_fields_mapped > 0:
                logger.info(f"   💎 Cost per field mapped: ${llm_stats['total_cost_usd']/total_fields_mapped:.6f}")
            logger.info(f"")
            
            # Return detailed statistics with local paths for operations
            return {
                "mapping_path": local_mapping_path,
                "radio_groups_path": local_radio_path,
                "field_statistics": {
                    "total_fields_in_pdf": total_fields_in_pdf,
                    "total_fields_mapped": total_fields_mapped,
                    "mapping_percentage": round(total_fields_mapped/total_fields_in_pdf*100, 1) if total_fields_in_pdf > 0 else 0,
                    "fields_by_type": field_type_counts,
                    "mapped_by_type": mapped_by_type,
                    "high_confidence_count": high_confidence_count,
                    "low_confidence_count": low_confidence_count,
                    "high_confidence_percentage": round(high_confidence_count/total_fields_mapped*100, 1) if total_fields_mapped > 0 else 0,
                    "low_confidence_percentage": round(low_confidence_count/total_fields_mapped*100, 1) if total_fields_mapped > 0 else 0
                },
                "performance": {
                    "total_time_seconds": round(total_time, 2),
                    "processing_rate_fields_per_sec": round(total_fields_mapped/total_time, 1) if total_time > 0 else 0,
                    "chunks_processed": len(context_dict),
                    "max_threads": self.max_threads,
                    "stage_timings": {
                        "data_loading": round(stage_timings['data_loading'], 2),
                        "key_enrichment": round(stage_timings['key_enrichment'], 2),
                        "chunking": round(stage_timings['chunking'], 2),
                        "radio_grouping": round(stage_timings['radio_grouping'], 2),
                        "chunk_processing": round(stage_timings['chunk_processing'], 2),
                        "result_saving": round(stage_timings['result_saving'], 2)
                    }
                },
                "llm_usage": {
                    "model": llm_stats['model'],
                    "total_calls": llm_stats['total_calls'],
                    "total_prompt_tokens": llm_stats['total_prompt_tokens'],
                    "total_completion_tokens": llm_stats['total_completion_tokens'],
                    "total_tokens": llm_stats['total_tokens'],
                    "total_cost_usd": round(llm_stats['total_cost_usd'], 6),
                    "avg_cost_per_call": round(llm_stats['total_cost_usd']/llm_stats['total_calls'], 6) if llm_stats['total_calls'] > 0 else 0,
                    "cost_per_field": round(llm_stats['total_cost_usd']/total_fields_mapped, 6) if total_fields_mapped > 0 else 0
                }
            }
            
        except (ValueError, FileNotFoundError, RuntimeError):
            raise
        except Exception as e:
            logger.error(f"Semantic mapping failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Semantic mapping process failed: {str(e)}") from e

    def map_fields_from_s3(self, s3_path: str, output_s3_path: str, radio_groups_s3_path: str = None, 
                          schema_type: str = "form_mapping", input_json_path: str = None):
        """
        Map fields from S3 extracted data to semantic keys.
        
        This method provides the interface expected by lambda handlers.
        
        Args:
            s3_path: S3 path to extracted JSON data
            output_s3_path: S3 path for mapping output
            radio_groups_s3_path: S3 path for radio groups output
            schema_type: Type of schema to use
            input_json_path: Path to input keys JSON (REQUIRED - must contain target mapping keys)
            
        Returns:
            Dictionary with processing results
        """
        import asyncio
        from src.core.config import get_processing_output_config
        
        logger.info(f"Starting S3-based field mapping from: {s3_path}")
        logger.info(f"Mapping output: {output_s3_path}")
        
        if radio_groups_s3_path:
            logger.info(f"Radio groups output: {radio_groups_s3_path}")
        else:
            # Auto-generate radio groups path using our config system
            processing_config = get_processing_output_config(s3_path)
            radio_groups_s3_path = processing_config["radio_groups_path"]
            logger.info(f"Auto-generated radio groups output: {radio_groups_s3_path}")
        
        # Handle input_json_path requirement
        if not input_json_path:
            # Try to auto-generate input keys path based on extracted JSON path
            logger.info("No input_json_path provided. Attempting to auto-generate based on file naming convention.")
            
            if s3_path.startswith("s3://"):
                # Generate input keys path from extracted JSON path
                # Example: s3://bucket/document_extracted.json -> s3://bucket/document_input_keys.json
                if s3_path.endswith("_extracted.json"):
                    base_path = s3_path[:-15]  # Remove "_extracted.json"
                    input_json_path = f"{base_path}_input_keys.json"
                else:
                    # Fallback: replace .json with _input_keys.json
                    base_path = s3_path.rsplit('.json', 1)[0]
                    input_json_path = f"{base_path}_input_keys.json"
                    
                logger.info(f"Auto-generated input_json_path: {input_json_path}")
                
                # Check if the input keys file exists
                from src.clients.s3_client import S3Client
                s3_client = S3Client()
                if not s3_client.object_exists(input_json_path):
                    raise FileNotFoundError(
                        f"Required input keys file not found at: {input_json_path}\n"
                        f"The input keys JSON file is mandatory for semantic mapping. "
                        f"It should contain the target semantic keys that form fields will be mapped to.\n"
                        f"Please create this file with your target mapping keys or provide input_json_path parameter."
                    )
            else:
                # Local path handling
                if s3_path.endswith("_extracted.json"):
                    base_path = s3_path[:-15]  # Remove "_extracted.json"
                    input_json_path = f"{base_path}_input_keys.json"
                else:
                    base_path = s3_path.rsplit('.json', 1)[0]
                    input_json_path = f"{base_path}_input_keys.json"
                    
                logger.info(f"Auto-generated input_json_path: {input_json_path}")
                
                if not os.path.exists(input_json_path):
                    raise FileNotFoundError(
                        f"Required input keys file not found at: {input_json_path}\n"
                        f"The input keys JSON file is mandatory for semantic mapping. "
                        f"It should contain the target semantic keys that form fields will be mapped to.\n"
                        f"Please create this file with your target mapping keys or provide input_json_path parameter."
                    )
        
        logger.info(f"Using input keys from: {input_json_path}")
        
        # Create local storage config for save_json function
        mapping_storage_config = {
            "type": "local",
            "path": output_s3_path
        }
        
        radio_storage_config = {
            "type": "local",
            "path": radio_groups_s3_path
        }
        
        # Create storage config dict for process_and_save
        storage_config = {
            "output_path": output_s3_path,
            "radio_groups": radio_groups_s3_path,
            "mapping_storage": mapping_storage_config,
            "radio_storage": radio_storage_config
        }
        
        # Run async process_and_save
        try:
            s3_mapping_start = time.time()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result_path = loop.run_until_complete(
                self.process_and_save(
                    extracted_path=s3_path,
                    input_json_path=input_json_path,
                    original_pdf_path="",  # Not needed for current processing
                    storage_config=storage_config
                )
            )
            
            total_s3_time = time.time() - s3_mapping_start
            
            # Load results to get field counts
            field_counts = {"total": 0, "high_confidence": 0, "low_confidence": 0}
            try:
                if output_s3_path.startswith("s3://"):
                    from src.clients.s3_client import S3Client
                    s3_client = S3Client()
                    mapping_data = s3_client.load_json_from_s3(output_s3_path)
                else:
                    with open(output_s3_path, 'r') as f:
                        mapping_data = json.load(f)
                
                field_counts["total"] = len(mapping_data)
                for fid, (key, value, confidence) in mapping_data.items():
                    if confidence >= 0.7:
                        field_counts["high_confidence"] += 1
                    else:
                        field_counts["low_confidence"] += 1
            except Exception as e:
                logger.warning(f"Could not load mapping results for field counts: {e}")
            
            return {
                "status": "success",
                "mapping_path": result_path,
                "radio_groups_path": radio_groups_s3_path,
                "total_fields": field_counts["total"],
                "high_confidence_count": field_counts["high_confidence"],
                "low_confidence_count": field_counts["low_confidence"],
                "processing_time_seconds": round(total_s3_time, 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to process S3 mapping: {str(e)}")
            raise

