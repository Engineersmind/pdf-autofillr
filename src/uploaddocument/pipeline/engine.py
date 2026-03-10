# """ExtractionEngine — top-level orchestrator for the full pipeline."""
# from __future__ import annotations
# import os
# import time
# from typing import Optional

# from uploaddocument.readers.reader_factory import ReaderFactory
# from uploaddocument.extraction.extractor import Extractor
# from uploaddocument.pipeline.parallel_runner import ParallelRunner
# from uploaddocument.pipeline.result import ExtractionResult
# from uploaddocument.logging.api_logger import APILogger


# class ExtractionEngine:
#     """
#     Orchestrates the full 8-step document extraction pipeline.

#     Sequential:
#         1. Load schema from SchemaConfig
#         2. Read document text via ReaderFactory

#     Parallel:
#         Thread A: 3. LLM extract  →  4. Save extraction_result + extraction_result_flat
#         Thread B: 5. make_embed   →  6. poll check_embed (Steps 3+5 of PDF Lambda)

#     Sequential:
#         7. fill_pdf (after both threads complete)
#         8. Save execution_logs.json + fire telemetry summary event
#     """

#     def __init__(
#         self,
#         openai_api_key: str,
#         schema_config,
#         storage,
#         pdf_filler=None,
#         settings=None,
#         prompt_builder=None,
#         telemetry=None,
#     ):
#         self.extractor = Extractor(openai_api_key=openai_api_key, prompt_builder=prompt_builder)
#         self.schema_config = schema_config
#         self.storage = storage
#         self.telemetry = telemetry
#         self.runner = ParallelRunner(
#             pdf_filler=pdf_filler,
#             settings=settings,
#             telemetry=telemetry,
#         )

#     def process(
#         self,
#         document_path: str,
#         user_id: str,
#         session_id: str,
#         pdf_path: Optional[str] = None,
#         log_s3_uri: Optional[str] = None,
#     ) -> ExtractionResult:
#         """
#         Run the full pipeline for a single document.

#         Args:
#             document_path: Local path to the document (S3 download handled by client).
#             user_id:       User identifier.
#             session_id:    Session identifier.
#             pdf_path:      S3 path to blank PDF template (required for PDF filling mode).
#             log_s3_uri:    Optional S3 URI to upload execution_logs.json to.

#         Returns:
#             ExtractionResult — see pipeline/result.py for all fields.
#         """
#         t_start = time.time()
#         logger = APILogger()
#         logger.log_process(f"ExtractionEngine.process: user={user_id} session={session_id}")

#         document_format = os.path.splitext(document_path)[1].lower()
#         schema = self.schema_config.form_keys

#         # Step 2: read document text
#         try:
#             logger.log_process(f"Reading document: {document_path} (format={document_format})")
#             document_text = ReaderFactory.read(document_path)
#             logger.log_process(f"Document read: {len(document_text)} chars")
#         except Exception as e:
#             logger.log_error("Failed to read document", exception=e)
#             if self.telemetry:
#                 self.telemetry.track_error(user_id, session_id, type(e).__name__, "read")
#             result = ExtractionResult(
#                 user_id=user_id,
#                 session_id=session_id,
#                 document_format=document_format,
#             )
#             result.errors.append(f"Document read error: {e}")
#             result.total_duration = round(time.time() - t_start, 3)
#             return result

#         # Steps 3–7: parallel extraction + embed + fill
#         result = self.runner.run(
#             document_text=document_text,
#             extractor=self.extractor,
#             schema=schema,
#             storage=self.storage,
#             user_id=user_id,
#             session_id=session_id,
#             pdf_path=pdf_path,
#             document_format=document_format,
#             logger=logger,
#         )

#         result.total_duration = round(time.time() - t_start, 3)

#         # Step 8a: save execution logs locally
#         logger.print_summary()
#         log_data = logger.get_summary()
#         log_data["result_summary"] = result.summary()
#         self.storage.save_execution_logs(user_id, session_id, log_data)

#         # Step 8b: optionally save logs to a specific S3 URI
#         if log_s3_uri:
#             logger.save_logs_to_s3(log_s3_uri)
#             result.s3_logs_uri = log_s3_uri

#         # Step 8c: fire telemetry summary event
#         if self.telemetry:
#             self.telemetry.track_document_processed(
#                 user_id=user_id,
#                 session_id=session_id,
#                 document_format=document_format,
#                 total_duration_seconds=result.total_duration,
#                 pdf_filled=result.pdf_result is not None,
#                 success=result.success,
#             )

#         return result















"""ExtractionEngine — top-level orchestrator for the full pipeline.

Changes from original
---------------------
- process() now accepts pdf_doc_id, filled_doc_pdf_id, investor_type and
  forwards them to runner.run(). These are required by DocUploadManagedPDFFiller
  and are ignored by any other filler or when pdf_filler=None.
"""
from __future__ import annotations
import os
import time
from typing import Optional

from uploaddocument.readers.reader_factory import ReaderFactory
from uploaddocument.extraction.extractor import Extractor
from uploaddocument.pipeline.parallel_runner import ParallelRunner
from uploaddocument.pipeline.result import ExtractionResult
from uploaddocument.logging.api_logger import APILogger


class ExtractionEngine:
    """
    Orchestrates the full 8-step document extraction pipeline.

    Sequential:
        1. Load schema from SchemaConfig
        2. Read document text via ReaderFactory

    Parallel:
        Thread A: 3. LLM extract  →  4. Save extraction_result + extraction_result_flat
        Thread B: 5. make_embed   →  6. poll check_embed (Steps 3+5 of PDF Lambda)

    Sequential:
        7. fill_pdf (after both threads complete)
        8. Save execution_logs.json + fire telemetry summary event
    """

    def __init__(
        self,
        openai_api_key: str,
        schema_config,
        storage,
        pdf_filler=None,
        settings=None,
        prompt_builder=None,
        telemetry=None,
    ):
        self.extractor = Extractor(openai_api_key=openai_api_key, prompt_builder=prompt_builder)
        self.schema_config = schema_config
        self.storage = storage
        self.telemetry = telemetry
        self.runner = ParallelRunner(
            pdf_filler=pdf_filler,
            settings=settings,
            telemetry=telemetry,
        )

    def process(
        self,
        document_path: str,
        user_id: str,
        session_id: str,
        pdf_path: Optional[str] = None,
        log_s3_uri: Optional[str] = None,
        # ── Lambda-specific fields — only used when filler is DocUploadManagedPDFFiller ──
        pdf_doc_id: str = "",
        filled_doc_pdf_id: str = "",
        investor_type: str = "Individual",
    ) -> ExtractionResult:
        """
        Run the full pipeline for a single document.

        Args:
            document_path:    Local path to the document (S3 download handled by client).
            user_id:          User identifier.
            session_id:       Session identifier.
            pdf_path:         S3 path to blank PDF template. Required for PDF fill mode.
            log_s3_uri:       Optional S3 URI to upload execution_logs.json to.
            pdf_doc_id:       ID of the blank PDF in your PDF service (int-castable string).
                              Required when using DocUploadManagedPDFFiller.
            filled_doc_pdf_id: ID used for S3 output paths in your PDF service.
                              Required when using DocUploadManagedPDFFiller.
            investor_type:    Passed to make_embed_file. Default: "Individual".

        Returns:
            ExtractionResult — see pipeline/result.py for all fields.
        """
        t_start = time.time()
        logger = APILogger()
        logger.log_process(f"ExtractionEngine.process: user={user_id} session={session_id}")

        document_format = os.path.splitext(document_path)[1].lower()
        schema = self.schema_config.form_keys

        # Step 2: read document text
        try:
            logger.log_process(f"Reading document: {document_path} (format={document_format})")
            document_text = ReaderFactory.read(document_path)
            logger.log_process(f"Document read: {len(document_text)} chars")
        except Exception as e:
            logger.log_error("Failed to read document", exception=e)
            if self.telemetry:
                self.telemetry.track_error(user_id, session_id, type(e).__name__, "read")
            result = ExtractionResult(
                user_id=user_id,
                session_id=session_id,
                document_format=document_format,
            )
            result.errors.append(f"Document read error: {e}")
            result.total_duration = round(time.time() - t_start, 3)
            return result

        # Steps 3–7: parallel extraction + embed + fill
        result = self.runner.run(
            document_text=document_text,
            extractor=self.extractor,
            schema=schema,
            storage=self.storage,
            user_id=user_id,
            session_id=session_id,
            pdf_path=pdf_path,
            document_format=document_format,
            logger=logger,
            pdf_doc_id=pdf_doc_id,
            filled_doc_pdf_id=filled_doc_pdf_id,
            investor_type=investor_type,
        )

        result.total_duration = round(time.time() - t_start, 3)

        # Step 8a: save execution logs to storage
        logger.print_summary()
        log_data = logger.get_summary()
        log_data["result_summary"] = result.summary()
        self.storage.save_execution_logs(user_id, session_id, log_data)

        # Step 8b: optionally save logs to a specific S3 URI
        if log_s3_uri:
            logger.save_logs_to_s3(log_s3_uri)
            result.s3_logs_uri = log_s3_uri

        # Step 8c: fire telemetry summary event
        if self.telemetry:
            self.telemetry.track_document_processed(
                user_id=user_id,
                session_id=session_id,
                document_format=document_format,
                total_duration_seconds=result.total_duration,
                pdf_filled=result.pdf_result is not None,
                success=result.success,
            )

        return result