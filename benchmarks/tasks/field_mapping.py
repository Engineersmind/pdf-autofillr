"""
Task: field_mapping

Measures how accurately an LLM maps PDF form fields to schema keys.

Metrics: Mapping Accuracy (exact), Mapping Accuracy (fuzzy), Avg Confidence
"""


def run(pdf_path: str, schema_keys_path: str, ground_truth: dict, model: str) -> dict:
    """
    Run field mapping on a PDF and score against ground truth.

    Args:
        pdf_path: Path to the PDF file.
        schema_keys_path: Path to the schema keys JSON.
        ground_truth: Loaded ground truth dict from datasets/<category>/ground_truth/.
        model: Model name as defined in models/ (e.g. "gpt-4o-mini").

    Returns:
        {
            "accuracy_exact": float,      # % fields mapped to exactly correct key
            "accuracy_fuzzy": float,      # % with partial token overlap
            "avg_confidence": float,      # mean model confidence score
            "correct": int,
            "total_mappable": int,
            "latency_ms": float,
            "cost_usd": float,
            "tokens_used": int,
        }
    """
    raise NotImplementedError("field_mapping task not yet implemented")
