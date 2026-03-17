"""
Metric: fill_accuracy

Scores filled PDF field values against expected values.
"""


def fill_accuracy(filled_values: dict, expected_values: dict) -> float:
    """
    Percentage of fields filled with the correct value.

    Comparison is normalised: lowercase, stripped whitespace, no punctuation.

    Args:
        filled_values: {field_id: filled_value_str}
        expected_values: {field_id: expected_value_str}

    Returns:
        Accuracy as a float between 0 and 1.
    """
    raise NotImplementedError


def _normalize(value: str) -> str:
    """Normalise a field value for comparison."""
    import re
    return re.sub(r"[^\w\s]", "", value.lower().strip())
