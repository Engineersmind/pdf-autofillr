"""Full pipeline — extract document + fill PDF via document_upload_managed."""
import os
from uploaddocument import UploadDocumentClient, S3Storage, SchemaConfig
from document_upload_managed.filler import DocUploadManagedPDFFiller

client = UploadDocumentClient(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    storage=S3Storage(
        static_bucket=os.environ["STATIC_BUCKET"],
        output_bucket=os.environ["OUTPUT_BUCKET"],
    ),
    schema_config=SchemaConfig.from_s3(
        f"s3://{os.environ['STATIC_BUCKET']}/configs/form_keys.json"
    ),
    pdf_filler=DocUploadManagedPDFFiller(
        auth0_domain=os.environ["AUTH0_DOMAIN"],
        auth0_client_id=os.environ["AUTH0_CLIENT_ID"],
        auth0_client_secret=os.environ["AUTH0_CLIENT_SECRET"],
        auth0_audience=os.environ["AUTH0_AUDIENCE"],
        pdf_lambda_url=os.environ["FILL_PDF_LAMBDA_URL"],
        pdf_api_key=os.environ["PDF_API_KEY"],
    ),
)

result = client.process_document(
    document_path="s3://my-input-bucket/docs/investor_pack.pdf",
    user_id="investor_123",
    session_id="session_abc",
    pdf_path=f"s3://{os.environ['STATIC_BUCKET']}/blank/subscription_agreement.pdf",
)

print("Extracted:", result.fields_extracted, "fields")
print("PDF result:", result.pdf_result)
