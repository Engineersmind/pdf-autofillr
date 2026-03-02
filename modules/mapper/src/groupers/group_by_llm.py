import re
import json
import logging
from src.groupers.base_grouper import BaseGrouper

logger = logging.getLogger(__name__)

class GroupByLLM(BaseGrouper):
    def __init__(self, extracted_data: dict, **kwargs):
        super().__init__(extracted_data, **kwargs)
        self.field_type = self.params.get("field_type", "RADIOBUTTON")
        self.threshold = self.params.get("threshold", 2)
        self.llm = self.params.get("llm", None)
        self.keys_data = self.params.get("keys_data", {})

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

        # Prepare the semantic keys/description section
        keys_data_section = ""
        if hasattr(self, "keys_data") and self.keys_data:
            keys_data_section = (
                "You are also provided with a dictionary of semantic keys and their descriptions:\n"
                f"{json.dumps(self.keys_data, indent=2)}\n"
                "- For each group, if the group’s context or label closely matches a description from this dictionary, "
                "use the corresponding key (the dictionary key, not the description) as the group’s description (set the 'description' field to that key string exactly).\n"
                "- If no match is found, generate a new, crisp, context-driven description for the group as before.\n"
            )

        prompt = f"""
    You are given lines extracted from a PDF form. Some lines contain tokens like {field_token}, which represent individual {self.field_type.lower()} fields.

    {keys_data_section}
    Your task is to:
    1. Group related {self.field_type.lower()}s together (such as titles like Mr, Mrs, or other options).
    2. For each group, if a description from the provided keys matches the group’s context, use the corresponding key as the group's description (set the 'description' field to that key string exactly).
    3. Otherwise, assign a short and meaningful description to each group, it should be crisp and sharp.
    4. Only use the numeric ID (e.g., 29, 30) from each [{field_type_upper}_FIELD:X] token.
    5. Return a clean JSON object with the following format exactly: We don't need any explanation, headers or any others things in reponse. only json output like below.
    6. Get correct export value or subname if is it radio button for that corresponding field id else return empty list

    {{
    "group_1": {{
        "{output_key}": [29, 30, 31],
        "export_values" : [Mr, Mrs, Dr],
        "description": "matched_key_or_generated_description"
    }},
    "group_2": {{
        "{output_key}": [45, 46],
        "export_values": [yes, no],
        "description": "matched_key_or_generated_description"
    }}
    }}

    Here is the extracted text (which may be partial and not the full page):

    {text}
    """
        logger.info("Starting field grouping using LLM")
        
        try:
            if not self.llm:
                raise ValueError("LLM is not initialized")
            
            raw_response = self.llm.complete(prompt)
            
            if not raw_response or not hasattr(raw_response, 'text'):
                raise ValueError("LLM returned empty or invalid response")
            
            cleaned_json = re.sub(r"^```json\n?|```$", "", raw_response.text.strip(), flags=re.MULTILINE)
            
            if not cleaned_json.strip():
                raise ValueError("LLM response is empty after cleaning")
            
            try:
                parsed = json.loads(cleaned_json)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM output as JSON. Output was: {repr(cleaned_json)}")
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
            dict: Grouped fields
            
        Raises:
            RuntimeError: If grouping fails
        """
        try:
            # Step 1: Extract relevant text lines around fields
            lines = self.get_context_lines()
            
            if not lines:
                logger.warning(f"No {self.field_type} fields found to group")
                return {}
            
            # Step 2: Use LLM to group fields from text
            groups = self.group_fields_from_text(lines)
            return groups
            
        except Exception as e:
            logger.error(f"Field grouping failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to group {self.field_type} fields: {str(e)}") from e
