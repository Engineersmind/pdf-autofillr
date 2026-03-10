"""FastAPI local development server for upload-document-sdk."""
from __future__ import annotations
import os
import tempfile
import uuid
from typing import Optional

try:
    from fastapi import FastAPI, File, Form, UploadFile, HTTPException
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    raise ImportError("Install server deps: pip install upload-document-sdk[server]")

from uploaddocument import UploadDocumentClient, LocalStorage, SchemaConfig

app = FastAPI(title="Upload Document SDK — Local Dev Server", version="0.1.0")

_client: Optional[UploadDocumentClient] = None


def get_client() -> UploadDocumentClient:
    global _client
    if _client is None:
        _client = UploadDocumentClient(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            storage=LocalStorage(
                data_path=os.getenv("UPLOAD_DOC_DATA_PATH", "./uploaddoc_data"),
                config_path=os.getenv("UPLOAD_DOC_CONFIG_PATH", "./configs"),
            ),
            schema_config=SchemaConfig.from_directory(
                os.getenv("UPLOAD_DOC_CONFIG_PATH", "./configs")
            ),
            pdf_filler=None,
        )
    return _client


@app.post("/extract")
async def extract_document(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: str = Form(default=""),
    pdf_path: str = Form(default=""),
):
    """Upload a document and extract structured data from it."""
    if not session_id:
        session_id = str(uuid.uuid4())

    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        client = get_client()
        result = client.process_document(
            document_path=tmp_path,
            user_id=user_id,
            session_id=session_id,
            pdf_path=pdf_path or None,
        )
        return JSONResponse({
            "user_id": result.user_id,
            "session_id": result.session_id,
            "method": result.method,
            "fields_extracted": result.fields_extracted,
            "extracted_flat": result.extracted_flat,
            "pdf_result": result.pdf_result,
            "success": result.success,
            "errors": result.errors,
        })
    finally:
        os.unlink(tmp_path)


@app.get("/result/{user_id}/{session_id}")
async def get_result(user_id: str, session_id: str):
    """Retrieve previously extracted data for a session."""
    client = get_client()
    data = client.get_extraction_result(user_id, session_id)
    if not data:
        raise HTTPException(status_code=404, detail="No result found for this session")
    return JSONResponse(data)


@app.get("/health")
async def health():
    return {"status": "ok", "sdk": "upload-document-sdk"}


if __name__ == "__main__":
    uvicorn.run("server.local_server:app", host="0.0.0.0", port=8000, reload=True)
