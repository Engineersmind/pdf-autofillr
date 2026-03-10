"""
Upload Document Managed PDF Service — NOT included in the open source SDK.

Install privately from the document_upload_managed/ folder in this repo:
    pip install ./document_upload_managed

Then wire it:
    from document_upload_managed.filler import DocUploadManagedPDFFiller
    from uploaddocument import UploadDocumentClient

    client = UploadDocumentClient(
        ...,
        pdf_filler=DocUploadManagedPDFFiller(
            auth0_domain=os.environ["AUTH0_DOMAIN"],
            auth0_client_id=os.environ["AUTH0_CLIENT_ID"],
            auth0_client_secret=os.environ["AUTH0_CLIENT_SECRET"],
            auth0_audience=os.environ["AUTH0_AUDIENCE"],
            pdf_lambda_url=os.environ["FILL_PDF_LAMBDA_URL"],
            pdf_api_key=os.environ["PDF_API_KEY"],
        )
    )
"""

def __getattr__(name):
    if name == "DocUploadManagedPDFFiller":
        raise ImportError(
            f"{name} is not in the open source SDK.\n"
            "Install privately: pip install ./document_upload_managed"
        )
    raise AttributeError(f"module 'uploaddocument.managed' has no attribute {name!r}")
