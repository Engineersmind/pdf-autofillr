# """
# ParallelRunner — runs extraction and embed preparation in parallel.

# Thread A: read document → LLM extract → schema enforce → save to storage
# Thread B: make_embed_file (Lambda Step 3) → poll check_embed_file (Step 5)

# Both run simultaneously. fill_pdf (Step 6) runs only after BOTH are done.
# Telemetry events are fired at each stage.
# """
# from __future__ import annotations
# import os
# import threading
# import time
# from typing import Optional

# from uploaddocument.pipeline.result import ExtractionResult


# class ParallelRunner:
#     """
#     Runs Thread A (extraction) and Thread B (embed) concurrently,
#     then fires fill_pdf once both are complete.
#     """

#     def __init__(self, pdf_filler=None, settings=None, telemetry=None):
#         self.pdf_filler = pdf_filler
#         self.poll_interval = getattr(settings, "pdf_poll_interval", 10)
#         self.poll_timeout = getattr(settings, "pdf_poll_timeout", 480)
#         self.max_retries = getattr(settings, "pdf_max_retries", 3)
#         self.telemetry = telemetry  # TelemetryCollector or None

#     def run(
#         self,
#         document_text: str,
#         extractor,
#         schema: dict,
#         storage,
#         user_id: str,
#         session_id: str,
#         pdf_path: Optional[str],
#         document_format: str = "",
#         logger=None,
#     ) -> ExtractionResult:
#         """Execute the full parallel pipeline and return ExtractionResult."""
#         result = ExtractionResult(
#             user_id=user_id,
#             session_id=session_id,
#             document_format=document_format,
#             fields_in_schema=self._count_schema_fields(schema),
#         )

#         # ── Thread A: extract + save ───────────────────────────────────
#         def thread_a():
#             t_start = time.time()
#             try:
#                 if logger:
#                     logger.log_process("Thread A: starting LLM extraction")
#                 cleaned, method = extractor.extract(document_text, schema, logger=logger)
#                 result.extracted_data = cleaned
#                 result.method = method
#                 result.extraction_latency = round(time.time() - t_start, 3)

#                 from uploaddocument.transform.dict_utils import flatten_dict
#                 flat = flatten_dict(cleaned)
#                 result.extracted_flat = flat
#                 result.fields_extracted = sum(1 for v in flat.values() if v not in ("", False, None))
#                 result.completion_pct = round(
#                     result.fields_extracted / max(result.fields_in_schema, 1) * 100, 1
#                 )

#                 storage.save_extraction_result(user_id, session_id, cleaned)
#                 storage.save_extraction_result_flat(user_id, session_id, flat)

#                 if logger:
#                     logger.log_process(
#                         f"Thread A: done — {result.fields_extracted}/{result.fields_in_schema} "
#                         f"fields ({result.completion_pct}%) via {method} in {result.extraction_latency}s"
#                     )

#                 # Telemetry: extraction event
#                 if self.telemetry:
#                     self.telemetry.track_extraction(
#                         user_id=user_id,
#                         session_id=session_id,
#                         document_format=document_format,
#                         fields_extracted=result.fields_extracted,
#                         fields_in_schema=result.fields_in_schema,
#                         latency_seconds=result.extraction_latency,
#                         method=method,
#                         success=True,
#                     )

#             except Exception as e:
#                 result.errors.append(f"Thread A extraction error: {e}")
#                 if logger:
#                     logger.log_error("Thread A failed", exception=e)
#                 if self.telemetry:
#                     self.telemetry.track_error(user_id, session_id, type(e).__name__, "extract")

#         # ── Thread B: embed prepare + poll ─────────────────────────────
#         def thread_b():
#             if not self.pdf_filler or not pdf_path:
#                 return
#             t_start = time.time()
#             try:
#                 if logger:
#                     logger.log_process("Thread B: calling make_embed_file (Step 3)")
#                 doc_id = self.pdf_filler.prepare_document(pdf_path, "document")
#                 session = storage.get_session_state(user_id, session_id) or {}
#                 session["pdf_doc_id"] = doc_id
#                 storage.save_session_state(user_id, session_id, session)

#                 if logger:
#                     logger.log_process(f"Thread B: polling check_embed_file (Step 5) — doc_id={doc_id}")
#                 ready = False
#                 deadline = time.time() + self.poll_timeout
#                 while time.time() < deadline:
#                     if self.pdf_filler.check_document_ready(doc_id):
#                         ready = True
#                         break
#                     time.sleep(self.poll_interval)

#                 if not ready:
#                     result.errors.append("Thread B: embed timed out")
#                     if self.telemetry:
#                         self.telemetry.track_error(user_id, session_id, "EmbedTimeout", "embed")
#                 else:
#                     if logger:
#                         logger.log_process("Thread B: embed ready")

#             except Exception as e:
#                 result.errors.append(f"Thread B embed error: {e}")
#                 if logger:
#                     logger.log_error("Thread B failed", exception=e)
#                 if self.telemetry:
#                     self.telemetry.track_error(user_id, session_id, type(e).__name__, "embed")

#         # ── Launch both threads ────────────────────────────────────────
#         ta = threading.Thread(target=thread_a, daemon=True)
#         tb = threading.Thread(target=thread_b, daemon=True)
#         ta.start()
#         tb.start()
#         ta.join()
#         tb.join()

#         # ── Step 6: fill_pdf (after both threads complete) ─────────────
#         if self.pdf_filler and pdf_path and not result.errors:
#             t_fill = time.time()
#             try:
#                 session = storage.get_session_state(user_id, session_id) or {}
#                 doc_id = session.get("pdf_doc_id")
#                 if doc_id:
#                     if logger:
#                         logger.log_process(f"fill_pdf (Step 6) — doc_id={doc_id}")
#                     for attempt in range(self.max_retries):
#                         try:
#                             fill_resp = self.pdf_filler.fill_document(doc_id, result.extracted_flat)
#                             result.pdf_result = fill_resp
#                             if logger:
#                                 logger.log_process(f"fill_pdf complete: {fill_resp}")
#                             break
#                         except Exception as e:
#                             if attempt == self.max_retries - 1:
#                                 raise
#                             time.sleep(5 * (attempt + 1))

#                     if self.telemetry:
#                         self.telemetry.track_pdf_fill(
#                             user_id=user_id,
#                             session_id=session_id,
#                             doc_id=doc_id,
#                             success=result.pdf_result is not None,
#                             duration_seconds=round(time.time() - t_fill, 3),
#                         )
#             except Exception as e:
#                 result.errors.append(f"fill_pdf error: {e}")
#                 if logger:
#                     logger.log_error("fill_pdf failed", exception=e)
#                 if self.telemetry:
#                     self.telemetry.track_error(user_id, session_id, type(e).__name__, "fill")

#         return result

#     @staticmethod
#     def _count_schema_fields(schema: dict, _count: list = None) -> int:
#         """Count total leaf fields in the schema."""
#         if _count is None:
#             _count = [0]
#         for v in schema.values():
#             if isinstance(v, dict):
#                 ParallelRunner._count_schema_fields(v, _count)
#             else:
#                 _count[0] += 1
#         return _count[0]





"""
ParallelRunner — runs extraction and embed preparation in parallel.

Thread A: LLM extract → schema enforce → save to storage
Thread B: make_embed_file (Lambda Step 3) → poll check_embed_file (Step 5)

Both run simultaneously. fill_pdf (Step 6) runs only after BOTH are done.
Telemetry events are fired at each stage.

Changes from original
---------------------
- run() now accepts pdf_doc_id, filled_doc_pdf_id, investor_type as kwargs.
  These are required by DocUploadManagedPDFFiller but are optional for any
  other PDFFillerInterface implementation that doesn't need them.
- Before Thread B starts, if the filler has a set_context() method it is
  called with (user_id, session_id, pdf_doc_id, filled_doc_pdf_id, investor_type).
  This is how the Lambda-specific fields reach the filler without polluting
  the abstract PDFFillerInterface signature.
- Thread B passes pdf_path AND investor_type to prepare_document() so generic
  filler implementations that need investor_type still work.
"""
from __future__ import annotations
import threading
import time
from typing import Optional

from uploaddocument.pipeline.result import ExtractionResult


class ParallelRunner:
    """
    Runs Thread A (extraction) and Thread B (embed) concurrently,
    then fires fill_pdf once both are complete.
    """

    def __init__(self, pdf_filler=None, settings=None, telemetry=None):
        self.pdf_filler = pdf_filler
        self.poll_interval = getattr(settings, "pdf_poll_interval", 10)
        self.poll_timeout = getattr(settings, "pdf_poll_timeout", 480)
        self.max_retries = getattr(settings, "pdf_max_retries", 3)
        self.telemetry = telemetry

    def run(
        self,
        document_text: str,
        extractor,
        schema: dict,
        storage,
        user_id: str,
        session_id: str,
        pdf_path: Optional[str],
        document_format: str = "",
        logger=None,
        # ── Lambda-specific fields (only used when filler is DocUploadManagedPDFFiller) ──
        pdf_doc_id: str = "",           # blank PDF's ID in your system (int-castable string)
        filled_doc_pdf_id: str = "",    # investor's filled-doc ID — used for S3 output paths
        investor_type: str = "Individual",
    ) -> ExtractionResult:
        """
        Execute the full parallel pipeline and return ExtractionResult.

        Args:
            document_text:    Extracted text from the source document.
            extractor:        Extractor instance (LLM + fallback).
            schema:           form_keys.json dict.
            storage:          StorageBackend instance.
            user_id:          User identifier (str — filler casts to int internally).
            session_id:       Session identifier.
            pdf_path:         S3 URI of the blank PDF template. Required for PDF fill mode.
            document_format:  File extension of the source document e.g. ".pdf".
            logger:           APILogger instance.
            pdf_doc_id:       ID of the blank PDF in your PDF service (int-castable string).
                              Required when using DocUploadManagedPDFFiller.
            filled_doc_pdf_id: ID used for S3 output paths in your PDF service.
                              Required when using DocUploadManagedPDFFiller.
            investor_type:    Investor type string passed to make_embed_file.
                              Default: "Individual".
        """
        result = ExtractionResult(
            user_id=user_id,
            session_id=session_id,
            document_format=document_format,
            fields_in_schema=self._count_schema_fields(schema),
        )

        # ── Inject context into filler BEFORE Thread B starts ─────────
        # DocUploadManagedPDFFiller.set_context() stores user_id, session_id,
        # pdf_doc_id, filled_doc_pdf_id, investor_type so all three interface
        # methods can read them. Other filler implementations that don't have
        # set_context() are silently skipped.
        if self.pdf_filler and pdf_path and hasattr(self.pdf_filler, "set_context"):
            self.pdf_filler.set_context(
                user_id=user_id,
                session_id=session_id,
                pdf_doc_id=pdf_doc_id,
                filled_doc_pdf_id=filled_doc_pdf_id,
                investor_type=investor_type,
            )
            if logger:
                logger.log_process(
                    f"ParallelRunner: filler context set — "
                    f"user_id={user_id}, session_id={session_id}, "
                    f"pdf_doc_id={pdf_doc_id}, filled_doc_pdf_id={filled_doc_pdf_id}, "
                    f"investor_type={investor_type}"
                )

        # ── Thread A: extract + save ───────────────────────────────────
        def thread_a():
            t_start = time.time()
            try:
                if logger:
                    logger.log_process("Thread A: starting LLM extraction")
                cleaned, method = extractor.extract(document_text, schema, logger=logger)
                result.extracted_data = cleaned
                result.method = method
                result.extraction_latency = round(time.time() - t_start, 3)

                from uploaddocument.transform.dict_utils import flatten_dict
                flat = flatten_dict(cleaned)
                result.extracted_flat = flat
                result.fields_extracted = sum(
                    1 for v in flat.values() if v not in ("", False, None)
                )
                result.completion_pct = round(
                    result.fields_extracted / max(result.fields_in_schema, 1) * 100, 1
                )

                storage.save_extraction_result(user_id, session_id, cleaned)
                storage.save_extraction_result_flat(user_id, session_id, flat)

                if logger:
                    logger.log_process(
                        f"Thread A: done — {result.fields_extracted}/{result.fields_in_schema} "
                        f"fields ({result.completion_pct}%) via {method} "
                        f"in {result.extraction_latency}s"
                    )

                if self.telemetry:
                    self.telemetry.track_extraction(
                        user_id=user_id,
                        session_id=session_id,
                        document_format=document_format,
                        fields_extracted=result.fields_extracted,
                        fields_in_schema=result.fields_in_schema,
                        latency_seconds=result.extraction_latency,
                        method=method,
                        success=True,
                    )

            except Exception as e:
                result.errors.append(f"Thread A extraction error: {e}")
                if logger:
                    logger.log_error("Thread A failed", exception=e)
                if self.telemetry:
                    self.telemetry.track_error(user_id, session_id, type(e).__name__, "extract")

        # ── Thread B: embed prepare + poll ─────────────────────────────
        def thread_b():
            if not self.pdf_filler or not pdf_path:
                return
            try:
                if logger:
                    logger.log_process("Thread B: calling make_embed_file (Step 3)")

                # investor_type is passed as document_type — the interface uses
                # the second argument for the document/investor type string.
                doc_id = self.pdf_filler.prepare_document(pdf_path, investor_type)

                # Persist the composite token so fill_pdf can retrieve it after
                # both threads complete.
                session_state = storage.get_session_state(user_id, session_id) or {}
                session_state["pdf_doc_id"] = doc_id
                storage.save_session_state(user_id, session_id, session_state)

                if logger:
                    logger.log_process(
                        f"Thread B: polling check_embed_file (Step 5) — token={doc_id!r}"
                    )

                ready = False
                deadline = time.time() + self.poll_timeout
                while time.time() < deadline:
                    if self.pdf_filler.check_document_ready(doc_id):
                        ready = True
                        break
                    time.sleep(self.poll_interval)

                if not ready:
                    result.errors.append(
                        f"Thread B: embed timed out after {self.poll_timeout}s"
                    )
                    if self.telemetry:
                        self.telemetry.track_error(
                            user_id, session_id, "EmbedTimeout", "embed"
                        )
                else:
                    if logger:
                        logger.log_process("Thread B: embed ready ✅")

            except Exception as e:
                result.errors.append(f"Thread B embed error: {e}")
                if logger:
                    logger.log_error("Thread B failed", exception=e)
                if self.telemetry:
                    self.telemetry.track_error(
                        user_id, session_id, type(e).__name__, "embed"
                    )

        # ── Launch both threads ────────────────────────────────────────
        ta = threading.Thread(target=thread_a, name="ExtractionThread", daemon=True)
        tb = threading.Thread(target=thread_b, name="EmbedThread", daemon=True)
        ta.start()
        tb.start()
        ta.join()
        tb.join()

        if logger:
            logger.log_process("Both threads complete — proceeding to fill_pdf")

        # ── Step 6: fill_pdf (after both threads complete) ─────────────
        if self.pdf_filler and pdf_path and not result.errors:
            t_fill = time.time()
            try:
                session_state = storage.get_session_state(user_id, session_id) or {}
                doc_id = session_state.get("pdf_doc_id")

                if not doc_id:
                    raise RuntimeError(
                        "fill_pdf: no pdf_doc_id in session state — "
                        "Thread B may have failed silently."
                    )

                if logger:
                    logger.log_process(f"fill_pdf (Step 6) — token={doc_id!r}")

                for attempt in range(self.max_retries):
                    try:
                        fill_resp = self.pdf_filler.fill_document(
                            doc_id, result.extracted_flat
                        )
                        result.pdf_result = fill_resp
                        if logger:
                            logger.log_process(f"fill_pdf complete ✅: {fill_resp}")
                        break
                    except Exception as e:
                        if attempt == self.max_retries - 1:
                            raise
                        wait = 5 * (attempt + 1)
                        if logger:
                            logger.log_process(
                                f"fill_pdf attempt {attempt + 1} failed, "
                                f"retrying in {wait}s: {e}"
                            )
                        time.sleep(wait)

                if self.telemetry:
                    self.telemetry.track_pdf_fill(
                        user_id=user_id,
                        session_id=session_id,
                        doc_id=doc_id,
                        success=result.pdf_result is not None,
                        duration_seconds=round(time.time() - t_fill, 3),
                    )

            except Exception as e:
                result.errors.append(f"fill_pdf error: {e}")
                if logger:
                    logger.log_error("fill_pdf failed", exception=e)
                if self.telemetry:
                    self.telemetry.track_error(
                        user_id, session_id, type(e).__name__, "fill"
                    )

        return result

    @staticmethod
    def _count_schema_fields(schema: dict, _count: list = None) -> int:
        """Count total leaf fields in the schema."""
        if _count is None:
            _count = [0]
        for v in schema.values():
            if isinstance(v, dict):
                ParallelRunner._count_schema_fields(v, _count)
            else:
                _count[0] += 1
        return _count[0]