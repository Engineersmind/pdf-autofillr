# chatbot-managed

**Private package — do not publish to PyPI.**

Implements `PDFFillerInterface` from the open-source `chatbot-sdk` using your
internal Auth0-authenticated PDF Lambda service.

---

## Installation

Install from the private repo directly:

```bash
pip install git+https://github.com/yourorg/chatbot-managed.git
# or locally:
pip install ./chatbot-managed
```

Requires `chatbot-sdk` to already be installed.

---

## Required environment variables

```dotenv
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_CLIENT_ID=your_auth0_client_id
AUTH0_CLIENT_SECRET=your_auth0_client_secret
AUTH0_AUDIENCE=https://your-api-audience

FILL_PDF_LAMBDA_URL=https://your-pdf-lambda-url.com
PDF_API_KEY=your_pdf_api_key

BACKEND_URL=https://your-backend-url.com
AUTH_TOKEN=your_internal_api_token
```

---

## Usage

```python
import os
from chatbot import chatbotClient, LocalStorage, FormConfig
from chatbot_managed.filler import chatbotManagedPDFFiller

client = chatbotClient(
    openai_api_key=os.environ["OPENAI_API_KEY"],
    storage=LocalStorage("./chatbot_data", "./configs"),
    form_config=FormConfig.from_directory("./configs"),
    pdf_filler=chatbotManagedPDFFiller(
        auth0_domain=os.environ["AUTH0_DOMAIN"],
        auth0_client_id=os.environ["AUTH0_CLIENT_ID"],
        auth0_client_secret=os.environ["AUTH0_CLIENT_SECRET"],
        auth0_audience=os.environ["AUTH0_AUDIENCE"],
        pdf_lambda_url=os.environ["FILL_PDF_LAMBDA_URL"],
        pdf_api_key=os.environ["PDF_API_KEY"],
        backend_url=os.environ["BACKEND_URL"],
        auth_token=os.environ["AUTH_TOKEN"],
    ),
)

client.create_session(
    user_id="investor_123",
    session_id="session_001",
    pdf_path="s3://your-bucket/blank_subscription_form.pdf",
)

response, complete, data = client.send_message("investor_123", "session_001", "")
```

---

## How it maps to the original Lambda steps

| SDK method | Lambda operation | When called |
|---|---|---|
| `prepare_document()` | `make_embed_file` | When investor type is selected |
| `check_document_ready()` | `check_embed_file` | Polled every 10s (configurable) |
| `fill_document()` | `fill_pdf` | After conversation completes |

Steps 1 and 2 (fetching the PDF doc ID from your backend REST API and uploading
the blank PDF to your static S3 bucket) happen in your existing backend before
the SDK session starts. Pass the resulting S3 key as `pdf_path` to `create_session()`.

---

## Auth0 token caching

The filler caches the Auth0 machine-to-machine token and only re-fetches it
60 seconds before expiry — so there is at most one Auth0 call per hour regardless
of how many PDF operations are triggered.
