"""S3 input + output mode."""
import os
from uploaddocument import UploadDocumentClient, S3Storage, SchemaConfig

client = UploadDocumentClient(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    storage=S3Storage(
        static_bucket=os.environ["STATIC_BUCKET"],
        output_bucket=os.environ["OUTPUT_BUCKET"],
    ),
    schema_config=SchemaConfig.from_s3(
        f"s3://{os.environ['STATIC_BUCKET']}/configs/form_keys.json"
    ),
    pdf_filler=None,
)

result = client.process_document(
    document_path="s3://my-input-bucket/docs/investor_pack.pdf",
    user_id="investor_123",
    session_id="session_abc",
    log_s3_uri=f"s3://{os.environ['OUTPUT_BUCKET']}/logs/execution_logs.json",
)
print(result.extracted_flat)
