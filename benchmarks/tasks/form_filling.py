"""
Task: form_filling

Measures how accurately an embedded PDF is filled with user data.

Metrics: Fill Accuracy %
"""


def run(embedded_pdf_path: str, user_data: dict, ground_truth: dict) -> dict:
    """
    Fill an embedded PDF and score the output against expected values.

    Args:
        embedded_pdf_path: Path to the embedded PDF (output of make_embed_file).
        user_data: User data dict to fill the form with.
        ground_truth: Expected field values.

    Returns:
        {
            "fill_accuracy": float,    # % fields filled with correct value
            "correct": int,
            "total_fields": int,
            "latency_ms": float,
        }
    """
    raise NotImplementedError("form_filling task not yet implemented")
