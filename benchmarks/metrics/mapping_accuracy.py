"""
Metric: mapping_accuracy

Scores LLM field-to-schema-key mapping against ground truth.
"""


def exact_accuracy(predictions: dict, ground_truth: dict) -> float:
    """
    Exact match accuracy: predicted_key == expected_key.

    Args:
        predictions: {field_id: {"schema_key": str, "confidence": float}}
        ground_truth: {field_id: {"expected_key": str | None, ...}}

    Returns:
        Accuracy as a float between 0 and 1.
    """
    raise NotImplementedError


def fuzzy_accuracy(predictions: dict, ground_truth: dict, threshold: float = 0.5) -> float:
    """
    Fuzzy match accuracy using token overlap between predicted and expected key.

    Args:
        predictions: {field_id: {"schema_key": str, "confidence": float}}
        ground_truth: {field_id: {"expected_key": str | None, ...}}
        threshold: Minimum token overlap ratio to count as a match.

    Returns:
        Accuracy as a float between 0 and 1.
    """
    raise NotImplementedError


def avg_confidence(predictions: dict) -> float:
    """Mean confidence score across all predicted mappings."""
    raise NotImplementedError
