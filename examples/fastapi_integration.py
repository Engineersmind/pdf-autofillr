"""FastAPI integration example with upload-document-sdk."""
import os
import tempfile
import uuid
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from uploaddocument import UploadDocumentClient, S3Storage, SchemaConfig

app = FastAPI()

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

@app.post("/extract")
async def extract(file: UploadFile = File(...), user_id: str = Form(...)):
    session_id = str(uuid.uuid4())
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = client.process_document(tmp_path, user_id=user_id, session_id=session_id)
        return JSONResponse({"session_id": session_id, "extracted": result.extracted_flat, "success": result.success})
    finally:
        os.unlink(tmp_path)
