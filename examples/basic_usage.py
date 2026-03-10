"""Basic usage — extract a local PDF, data-only mode (no PDF filling)."""
import os
from uploaddocument import UploadDocumentClient, LocalStorage, SchemaConfig

client = UploadDocumentClient(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    storage=LocalStorage(data_path="./data", config_path="./configs"),
    schema_config=SchemaConfig.from_directory("./configs"),
    pdf_filler=None,   # data-only mode
)

result = client.process_document(
    document_path="./investor_pack.pdf",
    user_id="investor_123",
    session_id="session_abc",
)

if result.success:
    print(f"Extracted {result.fields_extracted} fields via {result.method}")
    print(result.extracted_flat)
else:
    print("Errors:", result.errors)
