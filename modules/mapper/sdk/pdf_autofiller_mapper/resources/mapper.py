"""
Mapper Resource

Methods for PDF field extraction, mapping, embedding, and filling.
All endpoints live under the /mapper/ prefix.
"""

import os
from typing import Optional, Dict, Any, TYPE_CHECKING, Union
from pathlib import Path

if TYPE_CHECKING:
    from ..client import PDFMapperClient

_ALLOWED_FILENAMES = {"input.pdf", "global_schema.json", "input_data.json"}


class MapperResource:
    """
    Resource for mapper operations.

    Upload:
        upload_file() — multipart upload of input files (PDF / JSON schemas).

    High-level operations (derive all paths from IDs):
        make_embed_file, fill, fill_pdf, check_embed_file, run_all

    Low-level operations (explicit file paths):
        extract, map, embed
    """

    def __init__(self, client: "PDFMapperClient"):
        self.client = client

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def upload_file(
        self,
        user_id: str,
        session_id: str,
        pdf_doc_id: str,
        filename: str,
        source: Union[str, bytes, "os.PathLike[str]"],
    ) -> Dict[str, Any]:
        """
        Upload an input file to the mapper server.

        Places the file at:
            {MAPPER_INPUT_PATH}/{user_id}/{session_id}/{pdf_doc_id}/{filename}

        Args:
            user_id:    User identifier
            session_id: Session identifier
            pdf_doc_id: PDF document identifier
            filename:   One of ``"input.pdf"``, ``"global_schema.json"``,
                        or ``"input_data.json"``
            source:     Either a local file path (str / Path) or raw bytes

        Returns:
            ``{"status": "success", "path": ..., "size_bytes": ...}``

        Example::

            client.mapper.upload_file(
                user_id="1", session_id="1", pdf_doc_id="100",
                filename="input.pdf",
                source="/local/forms/application.pdf",
            )
            client.mapper.upload_file(
                user_id="1", session_id="1", pdf_doc_id="100",
                filename="global_schema.json",
                source="/local/schemas/keys.json",
            )
        """
        import httpx
        from ..exceptions import APIError, ConnectionError, TimeoutError

        if filename not in _ALLOWED_FILENAMES:
            raise ValueError(
                f"filename must be one of {sorted(_ALLOWED_FILENAMES)}, got {filename!r}"
            )

        if isinstance(source, (str, Path)):
            with open(source, "rb") as fh:
                data = fh.read()
        else:
            data = source

        url = f"/upload/{user_id}/{session_id}/{pdf_doc_id}/{filename}"
        try:
            # Send without JSON Content-Type header so httpx uses multipart
            response = self.client._http.post(
                url,
                files={"file": (filename, data)},
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Upload timed out for {filename}") from exc
        except (httpx.ConnectError, httpx.NetworkError) as exc:
            raise ConnectionError(
                f"Could not reach the mapper server at {self.client.base_url!r}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            body = ""
            try:
                body = exc.response.text
            except Exception:
                pass
            raise APIError(
                f"Upload failed with {exc.response.status_code}",
                status_code=exc.response.status_code,
                response_body=body,
            ) from exc

    # ------------------------------------------------------------------
    # Low-level operations (explicit file paths)
    # ------------------------------------------------------------------

    def extract(
        self,
        pdf_path: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        pdf_doc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract fields from a PDF file.

        Args:
            pdf_path: Path to PDF (local, S3 key, etc.)
            user_id: Optional user ID for tracking
            session_id: Optional session ID for tracking
            pdf_doc_id: Optional PDF document ID for tracking

        Returns:
            Extraction result with form fields
        """
        payload: Dict[str, Any] = {"pdf_path": pdf_path}
        if user_id is not None:
            payload["user_id"] = user_id
        if session_id is not None:
            payload["session_id"] = session_id
        if pdf_doc_id is not None:
            payload["pdf_doc_id"] = pdf_doc_id
        return self.client._request("POST", "/mapper/extract", json=payload)

    def map(
        self,
        extracted_json_path: str,
        input_json_path: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        pdf_doc_id: Optional[str] = None,
        investor_type: Optional[str] = "individual",
    ) -> Dict[str, Any]:
        """
        Map extracted fields to the target schema.

        Args:
            extracted_json_path: Path to the extracted fields JSON
            input_json_path: Path to the input data JSON
            user_id: Optional user ID for tracking
            session_id: Optional session ID for tracking
            pdf_doc_id: Optional PDF document ID for tracking
            investor_type: Investor type (default: "individual")

        Returns:
            Mapping result
        """
        payload: Dict[str, Any] = {
            "extracted_json_path": extracted_json_path,
            "input_json_path": input_json_path,
            "investor_type": investor_type,
        }
        if user_id is not None:
            payload["user_id"] = user_id
        if session_id is not None:
            payload["session_id"] = session_id
        if pdf_doc_id is not None:
            payload["pdf_doc_id"] = pdf_doc_id
        return self.client._request("POST", "/mapper/map", json=payload)

    def embed(
        self,
        original_pdf_path: str,
        extracted_json_path: str,
        mapping_json_path: str,
        radio_groups_path: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        pdf_doc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Embed field mappings into a PDF.

        Args:
            original_pdf_path: Path to the original PDF
            extracted_json_path: Path to the extracted fields JSON
            mapping_json_path: Path to the mapping JSON
            radio_groups_path: Path to the radio groups JSON
            user_id: Optional user ID for tracking
            session_id: Optional session ID for tracking
            pdf_doc_id: Optional PDF document ID for tracking

        Returns:
            Embed result
        """
        payload: Dict[str, Any] = {
            "original_pdf_path": original_pdf_path,
            "extracted_json_path": extracted_json_path,
            "mapping_json_path": mapping_json_path,
            "radio_groups_path": radio_groups_path,
        }
        if user_id is not None:
            payload["user_id"] = user_id
        if session_id is not None:
            payload["session_id"] = session_id
        if pdf_doc_id is not None:
            payload["pdf_doc_id"] = pdf_doc_id
        return self.client._request("POST", "/mapper/embed", json=payload)

    # ------------------------------------------------------------------
    # High-level operations (ID-based — paths resolved by the server)
    # ------------------------------------------------------------------

    def make_embed_file(
        self,
        user_id: str,
        session_id: str,
        pdf_doc_id: str,
        investor_type: Optional[str] = "individual",
        use_second_mapper: Optional[bool] = False,
    ) -> Dict[str, Any]:
        """
        Extract → Map → Embed pipeline in one call.

        The server resolves all file paths from (user_id, session_id, pdf_doc_id)
        using the MAPPER_* env vars.  Input files must already be at the
        configured input path before calling this method.

        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID
            investor_type: Investor type (default: "individual")
            use_second_mapper: Whether to use the RAG second mapper

        Returns:
            Result of the complete embed pipeline
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "pdf_doc_id": pdf_doc_id,
            "investor_type": investor_type,
            "use_second_mapper": use_second_mapper,
        }
        return self.client._request("POST", "/mapper/make-embed-file", json=payload)

    def fill(
        self,
        user_id: str,
        session_id: str,
        pdf_doc_id: str,
    ) -> Dict[str, Any]:
        """
        Fill a PDF form with data.

        The server resolves all file paths from (user_id, session_id, pdf_doc_id).
        The embedded PDF must have been produced by make_embed_file() first, and
        the input_data.json must be at the configured input path.

        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID

        Returns:
            Fill result
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "pdf_doc_id": pdf_doc_id,
        }
        return self.client._request("POST", "/mapper/fill", json=payload)

    def fill_pdf(
        self,
        user_id: str,
        session_id: str,
        pdf_doc_id: str,
    ) -> Dict[str, Any]:
        """
        Fill PDF (alias for fill with an alternate endpoint).

        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID

        Returns:
            Fill result
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "pdf_doc_id": pdf_doc_id,
        }
        return self.client._request("POST", "/mapper/fill-pdf", json=payload)

    def check_embed_file(
        self,
        user_id: str,
        session_id: str,
        pdf_doc_id: str,
    ) -> Dict[str, Any]:
        """
        Check whether the embedded PDF for this job exists and is ready.

        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID

        Returns:
            Status dict indicating whether the embedded file is ready
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "pdf_doc_id": pdf_doc_id,
        }
        return self.client._request("POST", "/mapper/check-embed-file", json=payload)

    def run_all(
        self,
        user_id: str,
        session_id: str,
        pdf_doc_id: str,
        investor_type: Optional[str] = "individual",
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline: Extract → Map → Embed → Fill.

        The server resolves all file paths from (user_id, session_id, pdf_doc_id).
        All three input files (input.pdf, global_schema.json, input_data.json)
        must be at the configured input path before calling this method.

        Args:
            user_id: User ID
            session_id: Session ID
            pdf_doc_id: PDF document ID
            investor_type: Investor type (default: "individual")

        Returns:
            Result of the complete pipeline
        """
        payload: Dict[str, Any] = {
            "user_id": user_id,
            "session_id": session_id,
            "pdf_doc_id": pdf_doc_id,
            "investor_type": investor_type,
        }
        return self.client._request("POST", "/mapper/run-all", json=payload)
