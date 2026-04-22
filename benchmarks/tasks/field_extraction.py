"""
Task: field_extraction

Measures how accurately the extractor detects all form fields in a PDF.

Metrics: Precision, Recall, F1
"""


def run(pdf_path: str, ground_truth: dict) -> dict:
    """
    Run field extraction on a PDF and score against ground truth.

    Args:
        pdf_path: Path to the PDF file.
        ground_truth: Loaded ground truth dict from datasets/<category>/ground_truth/.

    Returns:
        {
            "precision": float,
            "recall": float,
            "f1": float,
            "extracted_fields": int,
            "expected_fields": int,
        }
    """
    raise NotImplementedError("field_extraction task not yet implemented")
