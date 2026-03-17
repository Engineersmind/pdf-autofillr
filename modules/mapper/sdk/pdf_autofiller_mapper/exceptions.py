"""
PDF Autofiller SDK — Exception Hierarchy

All exceptions raised by the SDK descend from PDFMapperError so callers
can catch the whole family with a single except clause:

    try:
        result = mapper.process("form.pdf", "data.json")
    except PDFMapperError as e:
        print(f"SDK error: {e}")

Or catch individual stages for finer-grained handling:

    except MappingError as e:
        # LLM mapping failed — try a different model or lower threshold
        ...
    except FillingError as e:
        # Java fill stage failed
        ...
"""


class PDFMapperError(Exception):
    """
    Base class for all PDF Autofiller SDK errors.

    Every exception raised by PDFMapper or PDFMapperClient is a subclass
    of this, so ``except PDFMapperError`` catches everything from the SDK.
    """


# ── Configuration ─────────────────────────────────────────────────────────────

class ConfigurationError(PDFMapperError):
    """
    Invalid or missing SDK configuration.

    Raised when required parameters (llm_model, api_key, etc.) are missing
    or when required files (PDF, data JSON) do not exist before processing
    starts.

    Example triggers:
    - ``PDFMapper()`` called without ``llm_model``
    - Input PDF path does not exist
    - ``OPENAI_API_KEY`` not set and no ``api_key`` passed
    """


# ── Pipeline stages ───────────────────────────────────────────────────────────

class ExtractionError(PDFMapperError):
    """
    PDF field extraction failed.

    Raised when PyMuPDF / the extractor cannot read the PDF or finds no
    form fields.  The original exception is attached as ``__cause__``.
    """


class MappingError(PDFMapperError):
    """
    LLM mapping stage failed.

    Raised when the semantic mapper cannot match extracted fields to the
    input data keys — e.g. LLM API error, rate limit, or all fields mapped
    below the confidence threshold.
    """


class EmbeddingError(PDFMapperError):
    """
    Java embedding stage failed.

    Raised when ``rebuilder.jar`` exits with a non-zero code, times out,
    or the output embedded PDF is not produced.
    """


class FillingError(PDFMapperError):
    """
    Java filling stage failed.

    Raised when ``filler.jar`` exits with a non-zero code, times out,
    or the output filled PDF is not produced.
    """


# ── Network / server (API client) ─────────────────────────────────────────────

class APIError(PDFMapperError):
    """
    The mapper HTTP server returned an unexpected response.

    Attributes:
        status_code: HTTP status code (int), or None if no response was received.
        response_body: Raw response text for debugging.
    """

    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        base = super().__str__()
        if self.status_code:
            return f"{base} (HTTP {self.status_code})"
        return base


class ConnectionError(PDFMapperError):
    """
    Could not reach the mapper server.

    Raised when the HTTP client cannot connect — server is not running,
    wrong URL, or network unreachable.
    """


class TimeoutError(PDFMapperError):
    """
    Request to the mapper server timed out.

    LLM mapping calls can take 30–120 seconds.  Increase the ``timeout``
    parameter on ``PDFMapperClient`` if this fires regularly.
    """
