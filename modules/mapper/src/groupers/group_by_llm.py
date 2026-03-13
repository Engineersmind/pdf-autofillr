import json
import logging
from src.groupers.base_grouper import BaseGrouper
from src.prompts.renderer import render as render_prompt, build_messages
from src.utils.llm_json import parse_llm_json

logger = logging.getLogger(__name__)

class GroupByLLM(BaseGrouper):
    def __init__(self, extracted_data: dict, **kwargs):
        super().__init__(extracted_data, **kwargs)
        self.field_type = self.params.get("field_type", "RADIOBUTTON")
        self.threshold = self.params.get("threshold", 2)
        self.llm = self.params.get("llm", None)
        self.keys_data = self.params.get("keys_data", {})
        
        # Initialize cumulative LLM usage tracking
        self.total_llm_calls = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_cost_usd = 0.0

    def get_context_lines(self):
        radio_gids = set()
        # Step 1: Collect all RADIOBUTTON field GIDs
        for page in self.extracted_data["pages"]:
            for field in page.get("form_fields", []):
                if field.get("field_type", "").upper() == self.field_type.upper():
                    radio_gids.add(field["gid"])

        # Step 2: Expand to nearby GIDs based on threshold
        context_gid_set = set()
        for gid in radio_gids:
            context_gid_set.update(range(gid - self.threshold, gid + self.threshold + 1))

        # Step 3: Collect lines from text_elements if gid in context set
        collected_lines = []
        for page in self.extracted_data["pages"]:
            for text in page.get("text_elements", []):
                if text["gid"] in context_gid_set:
                    collected_lines.append((text["gid"], text["text"]))

        # Step 4: Sort by GID and return only text
        sorted_lines = [text for gid, text in sorted(collected_lines)]
        return sorted_lines

    def group_fields_from_text(self, lines):
        text = "\n".join(lines)
        field_type_upper = self.field_type.upper()
        field_token = f"[{field_type_upper}_FIELD:X]"
        output_key = f"{self.field_type.lower()}_fields"

        prompt = render_prompt(
            "groupers/field_grouping.j2",
            field_token=field_token,
            field_type_lower=self.field_type.lower(),
            field_type_upper=field_type_upper,
            output_key=output_key,
            keys_data=self.keys_data if hasattr(self, "keys_data") and self.keys_data else None,
            text=text,
        )
        logger.info("Starting field grouping using LLM")

        try:
            if not self.llm:
                raise ValueError("LLM is not initialized")

            # Use UnifiedLLMClient - returns LLMResponse with usage tracking
            messages = build_messages(self.llm.model, prompt)
            llm_response = self.llm.complete(messages)

            logger.debug(f"LLM Response Content:\n{repr(llm_response.content[:500])}")  # Log first 500 chars
            
            # Extract response and track cumulative usage
            usage = llm_response.usage
            self.total_llm_calls += 1
            self.total_prompt_tokens += usage.prompt_tokens
            self.total_completion_tokens += usage.completion_tokens
            self.total_cost_usd += usage.cost_usd
            
            logger.info(f"Field grouping LLM call - Tokens: {usage.total_tokens} (prompt: {usage.prompt_tokens}, completion: {usage.completion_tokens}), Cost: ${usage.cost_usd:.6f}")
            
            if not llm_response.content.strip():
                raise ValueError("LLM response is empty")

            try:
                parsed = parse_llm_json(llm_response.content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM output as JSON. Output was: {repr(llm_response.content)}")
                raise RuntimeError(f"LLM response is not valid JSON: {str(e)}") from e
            
            logger.info(f"Successfully grouped fields into {len(parsed)} groups")
            return parsed
            
        except (ValueError, RuntimeError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error during field grouping: {str(e)}", exc_info=True)
            raise RuntimeError(f"Field grouping failed: {str(e)}") from e



    def group(self):
        """
        Perform field grouping
        
        Returns:
            dict: Grouped fields with LLM usage stats
            
        Raises:
            RuntimeError: If grouping fails
        """
        try:
            # Step 1: Extract relevant text lines around fields
            lines = self.get_context_lines()
            
            if not lines:
                logger.warning(f"No {self.field_type} fields found to group")
                return {"groups": {}, "llm_usage": self._get_llm_usage_stats()}
            
            # Step 2: Use LLM to group fields from text
            groups = self.group_fields_from_text(lines)
            
            # Step 3: Log cumulative LLM stats
            self._log_cumulative_stats()
            
            return {
                "groups": groups,
                "llm_usage": self._get_llm_usage_stats()
            }
            
        except Exception as e:
            logger.error(f"Field grouping failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to group {self.field_type} fields: {str(e)}") from e
    
    def _get_llm_usage_stats(self):
        """Get cumulative LLM usage statistics"""
        total_tokens = self.total_prompt_tokens + self.total_completion_tokens
        avg_cost_per_call = self.total_cost_usd / self.total_llm_calls if self.total_llm_calls > 0 else 0.0
        
        return {
            "model": self.llm.model if self.llm else "unknown",
            "total_calls": self.total_llm_calls,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "avg_cost_per_call": avg_cost_per_call
        }
    
    def _log_cumulative_stats(self):
        """Log cumulative LLM usage statistics"""
        stats = self._get_llm_usage_stats()
        logger.info("=" * 80)
        logger.info("FIELD GROUPING LLM USAGE SUMMARY")
        logger.info(f"Model: {stats['model']}")
        logger.info(f"Total Calls: {stats['total_calls']}")
        logger.info(f"Total Prompt Tokens: {stats['total_prompt_tokens']:,}")
        logger.info(f"Total Completion Tokens: {stats['total_completion_tokens']:,}")
        logger.info(f"Total Tokens: {stats['total_tokens']:,}")
        logger.info(f"Total Cost: ${stats['total_cost_usd']:.6f}")
        logger.info(f"Average Cost per Call: ${stats['avg_cost_per_call']:.6f}")
        logger.info("=" * 80)
