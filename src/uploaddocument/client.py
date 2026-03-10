# """UploadDocumentClient — single entry point for the Upload Document SDK."""
# from __future__ import annotations
# import os
# import tempfile
# import time
# from typing import Optional

# from uploaddocument.config.schema_config import SchemaConfig
# from uploaddocument.config.settings import Settings
# from uploaddocument.pipeline.engine import ExtractionEngine
# from uploaddocument.pipeline.result import ExtractionResult
# from uploaddocument.pdf.interface import PDFFillerInterface
# from uploaddocument.storage.base import StorageBackend
# from uploaddocument.telemetry.collector import TelemetryCollector
# from uploaddocument.telemetry.config import TelemetryConfig
# from uploaddocument.telemetry.document_context import DocumentContext


# class UploadDocumentClient:
#     """
#     Single entry point for the Upload Document SDK.

#     ── Data-only mode (extract, no PDF fill) ──────────────────────────

#         client = UploadDocumentClient(
#             openai_api_key=os.environ["OPENAI_API_KEY"],
#             storage=LocalStorage("./data", "./configs"),
#             schema_config=SchemaConfig.from_directory("./configs"),
#             pdf_filler=None,
#         )
#         result = client.process_document(
#             document_path="./investor_pack.pdf",
#             user_id="user_123",
#             session_id="session_abc",
#         )
#         print(result.extracted_flat)
#         print(result.summary())

#     ── Full pipeline mode (extract + fill PDF) ─────────────────────────

#         from document_upload_managed.filler import DocUploadManagedPDFFiller
#         client = UploadDocumentClient(
#             ...,
#             pdf_filler=DocUploadManagedPDFFiller(...),
#         )
#         result = client.process_document(
#             document_path="s3://my-bucket/docs/investor_pack.pdf",
#             user_id="user_123",
#             session_id="session_abc",
#             pdf_path="s3://my-static-bucket/blank/subscription.pdf",
#         )
#         print(result.pdf_result)

#     ── With telemetry (self-hosted) ─────────────────────────────────────

#         from uploaddocument.telemetry import TelemetryConfig, DocumentContext
#         client = UploadDocumentClient(
#             ...,
#             telemetry=TelemetryConfig(
#                 enabled=True,
#                 mode="self_hosted",
#                 endpoint="https://telemetry.yourcompany.com/events",
#                 sdk_api_key="your_internal_key",
#             ),
#             document_context=DocumentContext(
#                 category="Private Markets",
#                 sub_category="Private Equity",
#                 document_type="LP Subscription Agreement",
#             ),
#         )

#     ── With telemetry (local/console) ───────────────────────────────────

#         from uploaddocument.telemetry import TelemetryConfig
#         client = UploadDocumentClient(
#             ...,
#             telemetry=TelemetryConfig(enabled=True, mode="local"),
#         )
#     """

#     def __init__(
#         self,
#         openai_api_key: str,
#         storage: StorageBackend,
#         schema_config: SchemaConfig,
#         pdf_filler: Optional[PDFFillerInterface] = None,
#         settings: Optional[Settings] = None,
#         prompt_builder=None,
#         telemetry: Optional[TelemetryConfig] = None,
#         document_context: Optional[DocumentContext] = None,
#     ):
#         self.storage = storage
#         self.schema_config = schema_config
#         self.settings = settings or Settings()

#         # Build telemetry collector (no-op if telemetry=None or enabled=False)
#         self.telemetry_collector = TelemetryCollector(
#             config=telemetry,
#             document_context=document_context,
#         )

#         self.engine = ExtractionEngine(
#             openai_api_key=openai_api_key,
#             schema_config=schema_config,
#             storage=storage,
#             pdf_filler=pdf_filler,
#             settings=self.settings,
#             prompt_builder=prompt_builder,
#             telemetry=self.telemetry_collector,
#         )

#     def process_document(
#         self,
#         document_path: str,
#         user_id: str,
#         session_id: str,
#         pdf_path: Optional[str] = None,
#         log_s3_uri: Optional[str] = None,
#     ) -> ExtractionResult:
#         """
#         Process a document end-to-end: read → extract → (optionally) fill PDF.

#         Args:
#             document_path: Local path OR S3 URI (s3://bucket/key) to the document.
#                            Supported formats: .pdf .docx .pptx .xlsx .json .txt
#             user_id:       Unique user identifier (hashed in telemetry, never plain-text).
#             session_id:    Unique session identifier (hashed in telemetry).
#             pdf_path:      S3 path to blank PDF template. Required for PDF filling mode.
#             log_s3_uri:    Optional S3 URI to upload the full execution_logs.json to.
#                            e.g. "s3://my-output-bucket/logs/exec_2024_01_01.json"

#         Returns:
#             ExtractionResult — call .summary() for a lightweight dict,
#             or access .extracted_flat for the full flat dict.

#         Raises:
#             ValueError:   If user_id or session_id are empty.
#             RuntimeError: If S3 download fails.
#         """
#         if not user_id or not session_id:
#             raise ValueError("user_id and session_id are required")

#         local_path = document_path
#         tmp_file = None

#         # Download from S3 if needed
#         if document_path.startswith("s3://"):
#             try:
#                 import boto3
#                 tmp_file = tempfile.NamedTemporaryFile(
#                     delete=False,
#                     suffix=os.path.splitext(document_path)[1]
#                 )
#                 bucket, key = document_path.replace("s3://", "").split("/", 1)
#                 boto3.client("s3").download_file(bucket, key, tmp_file.name)
#                 local_path = tmp_file.name
#                 tmp_file.close()
#             except Exception as e:
#                 raise RuntimeError(f"Failed to download document from S3: {e}")

#         try:
#             return self.engine.process(
#                 document_path=local_path,
#                 user_id=user_id,
#                 session_id=session_id,
#                 pdf_path=pdf_path,
#                 log_s3_uri=log_s3_uri,
#             )
#         finally:
#             if tmp_file and os.path.exists(tmp_file.name):
#                 os.unlink(tmp_file.name)

#     def get_extraction_result(self, user_id: str, session_id: str) -> Optional[dict]:
#         """Return the saved flat extraction result for a completed session."""
#         return self.storage.get_extraction_result_flat(user_id, session_id)

#     def list_sessions(self, user_id: str) -> list:
#         """List all session IDs for a user."""
#         return self.storage.list_user_sessions(user_id)

#     def delete_session(self, user_id: str, session_id: str) -> bool:
#         """Delete all stored data for a session."""
#         return self.storage.delete_session(user_id, session_id)
















"""UploadDocumentClient — single entry point for the Upload Document SDK."""
from __future__ import annotations
import os
import tempfile
import time
from typing import Optional

from uploaddocument.config.schema_config import SchemaConfig
from uploaddocument.config.settings import Settings
from uploaddocument.pipeline.engine import ExtractionEngine
from uploaddocument.pipeline.result import ExtractionResult
from uploaddocument.pdf.interface import PDFFillerInterface
from uploaddocument.storage.base import StorageBackend
from uploaddocument.telemetry.collector import TelemetryCollector
from uploaddocument.telemetry.config import TelemetryConfig
from uploaddocument.telemetry.document_context import DocumentContext


class UploadDocumentClient:
    """
    Single entry point for the Upload Document SDK.

    ── Data-only mode (extract, no PDF fill) ──────────────────────────

        client = UploadDocumentClient(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            storage=LocalStorage("./data", "./configs"),
            schema_config=SchemaConfig.from_directory("./configs"),
            pdf_filler=None,
        )
        result = client.process_document(
            document_path="./investor_pack.pdf",
            user_id="user_123",
            session_id="session_abc",
        )
        print(result.extracted_flat)
        print(result.summary())

    ── Full pipeline mode (extract + fill PDF via DocUploadManagedPDFFiller) ──

        from document_upload_managed.filler import DocUploadManagedPDFFiller
        client = UploadDocumentClient(
            openai_api_key=os.environ["OPENAI_API_KEY"],
            storage=S3Storage(
                static_bucket=os.environ["STATIC_BUCKET"],
                output_bucket=os.environ["OUTPUT_BUCKET"],
            ),
            schema_config=SchemaConfig.from_s3("s3://your-bucket/config/form_keys.json"),
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
            document_path="s3://your-bucket/docs/investor_pack.pdf",
            user_id="123",              # must be int-castable — matches your Lambda
            session_id="session_abc",
            pdf_path="s3://your-bucket/blank/subscription_form.pdf",
            pdf_doc_id="456",           # blank PDF's ID in your system
            filled_doc_pdf_id="789",    # investor's filled-doc ID (for S3 output paths)
            investor_type="Individual",
            log_s3_uri="s3://your-output-bucket/logs/exec_session_abc.json",
        )
        print(result.pdf_result)   # Lambda response — contains output S3 path
        print(result.success)

    ── With telemetry (self-hosted) ─────────────────────────────────────

        from uploaddocument.telemetry import TelemetryConfig, DocumentContext
        client = UploadDocumentClient(
            ...,
            telemetry=TelemetryConfig(
                enabled=True,
                mode="self_hosted",
                endpoint="https://telemetry.yourcompany.com/events",
                sdk_api_key="your_internal_key",
            ),
            document_context=DocumentContext(
                category="Private Markets",
                sub_category="Private Equity",
                document_type="LP Subscription Agreement",
            ),
        )

    ── With telemetry (local/console) ───────────────────────────────────

        from uploaddocument.telemetry import TelemetryConfig
        client = UploadDocumentClient(
            ...,
            telemetry=TelemetryConfig(enabled=True, mode="local"),
        )
    """

    def __init__(
        self,
        openai_api_key: str,
        storage: StorageBackend,
        schema_config: SchemaConfig,
        pdf_filler: Optional[PDFFillerInterface] = None,
        settings: Optional[Settings] = None,
        prompt_builder=None,
        telemetry: Optional[TelemetryConfig] = None,
        document_context: Optional[DocumentContext] = None,
    ):
        self.storage = storage
        self.schema_config = schema_config
        self.settings = settings or Settings()

        self.telemetry_collector = TelemetryCollector(
            config=telemetry,
            document_context=document_context,
        )

        self.engine = ExtractionEngine(
            openai_api_key=openai_api_key,
            schema_config=schema_config,
            storage=storage,
            pdf_filler=pdf_filler,
            settings=self.settings,
            prompt_builder=prompt_builder,
            telemetry=self.telemetry_collector,
        )

    def process_document(
        self,
        document_path: str,
        user_id: str,
        session_id: str,
        pdf_path: Optional[str] = None,
        log_s3_uri: Optional[str] = None,
        # ── Lambda-specific fields — only used with DocUploadManagedPDFFiller ──
        pdf_doc_id: str = "",
        filled_doc_pdf_id: str = "",
        investor_type: str = "Individual",
    ) -> ExtractionResult:
        """
        Process a document end-to-end: read → extract → (optionally) fill PDF.

        Args:
            document_path:    Local path OR S3 URI (s3://bucket/key) to the document.
                              Supported formats: .pdf .docx .pptx .xlsx .json .txt
            user_id:          Unique user identifier. Must be int-castable when using
                              DocUploadManagedPDFFiller (your Lambda requires integer IDs).
            session_id:       Unique session identifier.
            pdf_path:         S3 URI of the blank PDF template. Required for PDF fill mode.
            log_s3_uri:       Optional S3 URI to upload the full execution_logs.json to.
                              e.g. "s3://my-output-bucket/logs/exec_session_abc.json"
            pdf_doc_id:       ID of the blank PDF in your PDF service (int-castable string).
                              Required when using DocUploadManagedPDFFiller.
            filled_doc_pdf_id: ID used for S3 output paths in your PDF service (the
                              "filled doc" / left-side PDF ID). Required when using
                              DocUploadManagedPDFFiller.
            investor_type:    Passed to make_embed_file. Default: "Individual".
                              Examples: "Individual", "Corporation", "Trust", "LLC".

        Returns:
            ExtractionResult — call .summary() for a lightweight dict,
            or access .extracted_flat for the complete flat dict.

        Raises:
            ValueError:   If user_id or session_id are empty.
            RuntimeError: If S3 download fails.
        """
        if not user_id or not session_id:
            raise ValueError("user_id and session_id are required")

        local_path = document_path
        tmp_file = None

        # Download from S3 if needed
        if document_path.startswith("s3://"):
            try:
                import boto3
                tmp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=os.path.splitext(document_path)[1]
                )
                bucket, key = document_path.replace("s3://", "").split("/", 1)
                boto3.client("s3").download_file(bucket, key, tmp_file.name)
                local_path = tmp_file.name
                tmp_file.close()
            except Exception as e:
                raise RuntimeError(f"Failed to download document from S3: {e}") from e

        try:
            return self.engine.process(
                document_path=local_path,
                user_id=user_id,
                session_id=session_id,
                pdf_path=pdf_path,
                log_s3_uri=log_s3_uri,
                pdf_doc_id=pdf_doc_id,
                filled_doc_pdf_id=filled_doc_pdf_id,
                investor_type=investor_type,
            )
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)

    def get_extraction_result(self, user_id: str, session_id: str) -> Optional[dict]:
        """Return the saved flat extraction result for a completed session."""
        return self.storage.get_extraction_result_flat(user_id, session_id)

    def list_sessions(self, user_id: str) -> list:
        """List all session IDs for a user."""
        return self.storage.list_user_sessions(user_id)

    def delete_session(self, user_id: str, session_id: str) -> bool:
        """Delete all stored data for a session."""
        return self.storage.delete_session(user_id, session_id)