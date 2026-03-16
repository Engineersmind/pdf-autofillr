"""
Example: Using the PDF Autofiller Mapper SDK (embedded / in-process)

Prerequisites:
    pip install pdf-autofiller-mapper[embedded]
    # Also requires Java 17+ on PATH

    Copy modules/mapper/config.ini.example → modules/mapper/config.ini
    Set your LLM key (OPENAI_API_KEY, ANTHROPIC_API_KEY, or use Ollama)

Run from repo root:
    python examples/mapper_direct_usage.py
"""

from pdf_autofiller_mapper import PDFMapper

CONFIG = "modules/mapper/config.ini"
PDF_TEMPLATE = "data/modules/mapper_sample/input/small_4page.pdf"
SCHEMA_KEYS = "data/modules/mapper_sample/form_keys_flat.json"


def example_two_phase():
    """Standard two-phase workflow: embed once, fill many times."""

    mapper = PDFMapper(config_path=CONFIG)

    # Phase 1 — run once per PDF template
    # Extracts form fields, maps them to schema keys, bakes metadata into PDF
    print("Phase 1: make_embed_file ...")
    embed_result = mapper.make_embed_file(PDF_TEMPLATE, SCHEMA_KEYS)
    embed_result.save("output/form_embedded.pdf")
    print(f"  Embedded PDF saved: output/form_embedded.pdf")

    # Phase 2 — run once per user
    user_data = {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
        "dateOfBirth": "1990-05-14",
    }
    print("Phase 2: fill ...")
    fill_result = mapper.fill("output/form_embedded.pdf", user_data)
    fill_result.save("output/form_filled.pdf")
    print(f"  Filled PDF saved: output/form_filled.pdf")


def example_run_all():
    """Convenience: extract + map + embed + fill in one call."""

    mapper = PDFMapper(config_path=CONFIG)

    user_data = {"firstName": "John", "lastName": "Smith"}
    result = mapper.run_all(PDF_TEMPLATE, SCHEMA_KEYS, user_data)
    result.save("output/form_run_all.pdf")
    print(f"Filled PDF saved: output/form_run_all.pdf")


def example_check_embed():
    """Check whether a PDF already has embedded metadata."""

    mapper = PDFMapper(config_path=CONFIG)
    is_embedded = mapper.check_embed_file("output/form_embedded.pdf")
    print(f"Has embedded metadata: {is_embedded}")


if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)

    print("=== Two-phase workflow ===")
    example_two_phase()

    print("\n=== Check embed ===")
    example_check_embed()

    print("\n=== Run all (single call) ===")
    example_run_all()

    print("\nDone.")
