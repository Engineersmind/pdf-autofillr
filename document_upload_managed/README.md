# document-upload-managed

**PRIVATE** — do not publish to PyPI.

Implements `PDFFillerInterface` using your Auth0-authenticated PDF Lambda service.

## Install

```bash
pip install ./document_upload_managed
```

## Usage

```python
from document_upload_managed.filler import DocUploadManagedPDFFiller
from uploaddocument import UploadDocumentClient, LocalStorage, SchemaConfig

client = UploadDocumentClient(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    storage=LocalStorage("./data", "./configs"),
    schema_config=SchemaConfig.from_directory("./configs"),
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
    document_path="./investor_pack.pdf",
    user_id="user_123",
    session_id="session_abc",
    pdf_path="s3://my-static-bucket/blank/subscription.pdf",
)
print(result.pdf_result)
```
