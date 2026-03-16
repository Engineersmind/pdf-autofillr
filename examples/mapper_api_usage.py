"""
Example: Using the PDF Autofiller Mapper SDK (HTTP client)

Prerequisites:
    pip install pdf-autofiller-mapper

    Start the server first:
        cd modules/mapper && python api_server.py
        # → http://localhost:8000

Run from repo root:
    python examples/mapper_api_usage.py
"""

from pdf_autofiller_mapper import PDFMapperClient

SERVER = "http://localhost:8000"
PDF_TEMPLATE = "data/modules/mapper_sample/input/small_4page.pdf"
SCHEMA_KEYS = "data/modules/mapper_sample/form_keys_flat.json"


def example_health_check(client: PDFMapperClient):
    result = client.health()
    print(f"Server status: {result['status']}")


def example_two_phase(client: PDFMapperClient):
    """Standard two-phase workflow via HTTP."""

    # Phase 1 — embed (run once per template)
    print("Phase 1: make_embed_file ...")
    embed = client.mapper.make_embed_file(
        pdf_path=PDF_TEMPLATE,
        global_json_path=SCHEMA_KEYS,
    )
    print(f"  embedded pdf: {embed.get('embedded_pdf_path')}")

    # Phase 2 — fill (run once per user)
    print("Phase 2: fill ...")
    user_data = {
        "firstName": "Jane",
        "lastName": "Doe",
        "email": "jane.doe@example.com",
    }
    fill = client.mapper.fill(
        pdf_path=embed["embedded_pdf_path"],
        input_json=user_data,
    )
    print(f"  filled pdf: {fill.get('filled_pdf_path')}")


def example_extract_only(client: PDFMapperClient):
    """Extract form fields without filling."""
    result = client.mapper.extract(pdf_path=PDF_TEMPLATE)
    fields = result.get("fields", {})
    print(f"Extracted {len(fields)} fields: {list(fields.keys())[:5]} ...")


def example_run_all(client: PDFMapperClient):
    """Full pipeline in one call."""
    user_data = {"firstName": "John", "lastName": "Smith"}
    result = client.mapper.run_all(
        pdf_path=PDF_TEMPLATE,
        global_json_path=SCHEMA_KEYS,
        input_json=user_data,
    )
    print(f"run_all filled pdf: {result.get('filled_pdf_path')}")


if __name__ == "__main__":
    with PDFMapperClient(SERVER) as client:
        print("=== Health check ===")
        example_health_check(client)

        print("\n=== Extract fields ===")
        example_extract_only(client)

        print("\n=== Two-phase workflow ===")
        example_two_phase(client)

        print("\n=== Run all ===")
        example_run_all(client)

    print("\nDone.")
