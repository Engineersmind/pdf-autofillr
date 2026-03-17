"""
PDF Mapper — Embedded SDK

PDFMapper runs the complete extraction → mapping → embedding → filling pipeline
in-process (no server required).  Configuration is driven by the same
``config.ini`` file used by the mapper Docker service, so all LLM settings,
provider choices, and tuning live in one place.  API keys stay in environment
variables — never in the constructor.

Two-phase workflow
------------------
The embed pipeline (run **once per PDF template**):

    result = mapper.make_embed_file("form.pdf", "schema_keys.json")
    embedded_pdf = result.embedded_pdf   # reuse for many users

The fill pipeline (run **once per user**):

    result = mapper.fill(embedded_pdf, "user_data.json")
    result.save("filled_application.pdf")

Or run both in one call (convenient for one-off use):

    result = mapper.process("form.pdf", "schema_keys.json", "user_data.json")

JSON file semantics
-------------------
``global_json_path``  (used in the *embed* pipeline — extract / map / embed)
    Keys-only schema that tells the mapper what fields to expect.
    All values should be empty strings:
    ``{"firstName": "", "lastName": "", "dob": ""}``

``input_json_path``  (used in the *fill* pipeline)
    Actual per-user data — a subset of the global schema keys with real values:
    ``{"firstName": "Jane", "lastName": "Doe"}``

Supported LLM providers (set in config.ini [mapping] llm_model):
    gpt-4o, gpt-4o-mini                              → OpenAI
    claude-3-5-sonnet-20241022                        → Anthropic
    bedrock/anthropic.claude-3-5-sonnet-...-v2:0     → AWS Bedrock
    azure/gpt-4                                       → Azure OpenAI
    vertex_ai/gemini-pro                              → Google Vertex AI
    ollama/qwen2.5:14b, ollama/llama3.1:8b            → Ollama (local, free)

Environment variables for credentials (never passed to the constructor):
    OPENAI_API_KEY
    ANTHROPIC_API_KEY
    AZURE_API_KEY + AZURE_API_BASE + AZURE_API_VERSION
    AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS_REGION_NAME
    GOOGLE_APPLICATION_CREDENTIALS + VERTEX_PROJECT + VERTEX_LOCATION
    OLLAMA_API_BASE          (default: http://localhost:11434)
    PDF_AUTOFILLER_CONFIG    (auto-discovery fallback for config.ini path)

Two-LLM map phase:
    When use_second_mapper=True the map phase runs two models in parallel:
      [mapping]  llm_model         → primary semantic mapper
      [headers]  headers_llm_model → headers/RAG second mapper

Quick start (all settings from config.ini)::

    mapper = PDFMapper(config_path="config.ini")
    result = mapper.make_embed_file("form.pdf", "schema_keys.json")
    if result.ok:
        print(result.embedded_pdf)

Override a single setting without editing config.ini::

    mapper = PDFMapper(
        config_path="config.ini",
        llm_model="bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0",
    )

No config.ini — pass everything directly::

    mapper = PDFMapper(llm_model="gpt-4o", confidence_threshold=0.8)

Automatic temp-file cleanup via context manager::

    with PDFMapper(config_path="config.ini", cleanup=True) as mapper:
        result = mapper.process("form.pdf", "schema_keys.json", "user_data.json")
        result.save("filled.pdf")
"""

import asyncio
import os
import shutil
import time
from typing import Optional, Set

from .result import SDKResult
from .exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# Lazy import
# ---------------------------------------------------------------------------

def _import_mapper_internals():
    """
    Lazy-import the mapper module internals.

    Deferred so that ``import pdf_autofiller_mapper`` does not fail when the mapper
    module is not installed — only actual PDFMapper method calls will raise.
    """
    try:
        from src.handlers.operations import (  # noqa: PLC0415
            handle_extract_operation,
            handle_map_operation,
            handle_embed_operation,
            handle_fill_operation,
        )
        from src.configs.sdk import SDKStorageConfig    # noqa: PLC0415
        from src.utils.ini_config import IniConfigLoader  # noqa: PLC0415
        return (
            handle_extract_operation,
            handle_map_operation,
            handle_embed_operation,
            handle_fill_operation,
            SDKStorageConfig,
            IniConfigLoader,
        )
    except ImportError as exc:
        raise ConfigurationError(
            "PDFMapper embedded SDK requires the mapper module. "
            "Install with: pip install pdf-autofiller[embedded]\n"
            f"Detail: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# PDFMapper
# ---------------------------------------------------------------------------

class PDFMapper:
    """
    Embedded PDF form-filling SDK.

    Args:
        config_path:
            Path to ``config.ini``.  When omitted, the loader checks
            (in order): the ``PDF_AUTOFILLER_CONFIG`` env var, ``./config.ini``
            in the current directory, and the mapper module root.

        llm_model:
            Override ``[mapping] llm_model`` from config.ini.
            Uses LiteLLM format — the prefix determines the provider:
            ``"gpt-4o"`` (OpenAI), ``"ollama/llama3.1:8b"`` (local),
            ``"bedrock/..."`` (AWS Bedrock), ``"azure/gpt-4"`` (Azure).

        headers_llm_model:
            Override ``[headers] headers_llm_model`` — the second LLM used
            when ``use_second_mapper=True`` for the RAG/headers pipeline.

        confidence_threshold:
            Override ``[mapping] confidence_threshold`` (0–1, default 0.7).

        use_second_mapper:
            Override ``[mapping] use_second_mapper`` — enables the RAG +
            headers pipeline in parallel with the semantic mapper.

        output_dir:
            Directory for all intermediate and final output files.
            Created automatically if it does not exist.
            Defaults to a per-PDF temp directory (``/tmp/pdf_mapper_<stem>``).

        cleanup:
            Controls deletion of the ``output_dir`` after each operation:

            * ``False``          — keep all files (default)
            * ``True``           — always delete after every operation
            * ``"on_success"``   — delete only when the operation succeeds
            * ``"on_error"``     — delete only when the operation fails

            When used as a context manager, any remaining output directories
            are deleted on ``__exit__`` according to this policy.
    """

    _VALID_CLEANUP = (False, True, "on_success", "on_error")

    def __init__(
        self,
        config_path: Optional[str] = None,
        *,
        llm_model: Optional[str] = None,
        headers_llm_model: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        use_second_mapper: Optional[bool] = None,
        output_dir: Optional[str] = None,
        cleanup=False,
    ):
        if cleanup not in self._VALID_CLEANUP:
            raise ConfigurationError(
                f"cleanup must be one of {self._VALID_CLEANUP!r}, got {cleanup!r}"
            )

        # At least one of these must eventually resolve to an llm_model
        if not config_path and not llm_model and not os.environ.get("PDF_AUTOFILLER_CONFIG"):
            raise ConfigurationError(
                "Provide config_path='path/to/config.ini' or llm_model='gpt-4o'. "
                "Alternatively set the PDF_AUTOFILLER_CONFIG environment variable."
            )

        self._config_path = config_path
        self._output_dir = output_dir
        self._cleanup = cleanup

        # Only store overrides that were explicitly set (None = "don't override")
        self._overrides: dict = {
            k: v for k, v in {
                "llm_model": llm_model,
                "headers_llm_model": headers_llm_model,
                "confidence_threshold": confidence_threshold,
                "use_second_mapper": use_second_mapper,
            }.items()
            if v is not None
        }

        # Track output dirs created during this session for context-manager cleanup
        self._session_dirs: Set[str] = set()

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "PDFMapper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Clean up all session output dirs according to the cleanup policy."""
        success = exc_type is None
        if (
            self._cleanup is True
            or (self._cleanup == "on_success" and success)
            or (self._cleanup == "on_error" and not success)
        ):
            for d in self._session_dirs:
                if os.path.isdir(d):
                    shutil.rmtree(d, ignore_errors=True)
        return False  # never suppress exceptions

    # ── Primary operations ────────────────────────────────────────────────────

    def make_embed_file(self, pdf_path: str, global_json_path: str) -> SDKResult:
        """
        Preparation pipeline: extract → map → embed.

        Run this **once per PDF template** to produce an embedded PDF ready
        to be filled many times with different per-user data.

        Args:
            pdf_path:
                Path to the original (blank) PDF form.
            global_json_path:
                Path to the **global JSON schema** — a JSON file whose keys
                are the expected data fields and whose values are all empty
                (e.g. ``{"firstName": "", "lastName": ""}``).  This tells the
                map phase which fields the form should produce.

        Returns:
            SDKResult.  On success ``result.embedded_pdf`` is the prepared PDF.
        """
        _validate_pdf(pdf_path)
        _validate_json(global_json_path, "Global JSON schema")
        handle_extract, handle_map, handle_embed, _, SDKStorageConfig, _ = \
            _import_mapper_internals()

        cfg = self._make_embed_config(pdf_path, global_json_path, SDKStorageConfig)
        mapping_config = self._build_mapping_config()
        start = time.time()
        pipeline_results = {}

        extract_raw = self._run(handle_extract(cfg))
        pipeline_results["extract"] = extract_raw
        if extract_raw.get("status") != "success":
            return self._fail(extract_raw.get("error", "Extraction failed"),
                              cfg, time.time() - start)

        map_raw = self._run(handle_map(cfg, mapping_config))
        pipeline_results["map"] = map_raw
        if map_raw.get("status") != "success":
            return self._fail(map_raw.get("error", "Mapping failed"),
                              cfg, time.time() - start)

        embed_raw = self._run(handle_embed(cfg))
        pipeline_results["embed"] = embed_raw
        if embed_raw.get("status") != "success":
            return self._fail(embed_raw.get("error", "Embedding failed"),
                              cfg, time.time() - start)

        result = SDKResult.from_operation({
            "status": "success",
            "execution_time": time.time() - start,
            "pipeline_results": pipeline_results,
        })
        result.embedded_pdf = cfg.local_embedded_pdf
        self._post_op(success=True, cfg=cfg)
        return result

    def fill(self, pdf_path: str, input_json_path: str) -> SDKResult:
        """
        Fill pipeline: fill only.

        Requires the PDF to have already been prepared by ``make_embed_file()``.
        Pass the embedded PDF path produced by that stage.

        Args:
            pdf_path:
                Path to the **embedded PDF** produced by ``make_embed_file()``.
            input_json_path:
                Path to the **per-user data JSON** — the actual values to fill
                into the form (e.g. ``{"firstName": "Jane", "lastName": "Doe"}``).
                This is a subset of the global schema keys, with real values.

        Returns:
            SDKResult.  On success ``result.filled_pdf`` is the filled PDF.
        """
        _validate_pdf(pdf_path)
        _validate_json(input_json_path, "Input data JSON")
        _, _, _, handle_fill, SDKStorageConfig, _ = _import_mapper_internals()

        cfg = self._make_fill_config(pdf_path, input_json_path, SDKStorageConfig)
        start = time.time()
        raw = self._run(handle_fill(cfg))
        if raw.get("status") != "success":
            return self._fail(raw.get("error", "Filling failed"), cfg, time.time() - start)

        result = SDKResult.from_operation(
            {
                "status": "success",
                "execution_time": time.time() - start,
                "pipeline_results": {"fill": raw},
            },
            filled_pdf=raw.get("output_file") or cfg.local_filled_pdf,
        )
        self._post_op(success=True, cfg=cfg)
        return result

    def process(
        self,
        pdf_path: str,
        global_json_path: str,
        input_json_path: str,
    ) -> SDKResult:
        """
        Full pipeline: extract → map → embed → fill.

        Convenience wrapper — equivalent to ``make_embed_file()`` followed
        immediately by ``fill()``, sharing the same output directory.

        Args:
            pdf_path:
                Path to the original (blank) PDF form.
            global_json_path:
                Global JSON schema (keys only, empty values) — used by the
                extract / map / embed stages.
            input_json_path:
                Per-user data JSON (actual values) — used by the fill stage.

        Returns:
            SDKResult.  On success both ``result.embedded_pdf`` and
            ``result.filled_pdf`` are set.
        """
        _validate_pdf(pdf_path)
        _validate_json(global_json_path, "Global JSON schema")
        _validate_json(input_json_path, "Input data JSON")
        (handle_extract, handle_map, handle_embed, handle_fill,
         SDKStorageConfig, _) = _import_mapper_internals()

        # Embed stages use global_json; fill stage uses input_json.
        # Both configs share the same output_dir so intermediate files are visible.
        embed_cfg = self._make_embed_config(pdf_path, global_json_path, SDKStorageConfig)
        fill_cfg  = self._make_fill_config(pdf_path, input_json_path, SDKStorageConfig)

        mapping_config = self._build_mapping_config()
        start = time.time()
        pipeline_results = {}

        for stage_name, coro_fn in [
            ("extract", lambda: handle_extract(embed_cfg)),
            ("map",     lambda: handle_map(embed_cfg, mapping_config)),
            ("embed",   lambda: handle_embed(embed_cfg)),
            ("fill",    lambda: handle_fill(fill_cfg)),
        ]:
            raw = self._run(coro_fn())
            pipeline_results[stage_name] = raw
            if raw.get("status") != "success":
                return self._fail(
                    raw.get("error", f"{stage_name.capitalize()} failed"),
                    embed_cfg, time.time() - start,
                )

        result = SDKResult.from_operation(
            {
                "status": "success",
                "execution_time": time.time() - start,
                "pipeline_results": pipeline_results,
            },
            filled_pdf=fill_cfg.local_filled_pdf,
        )
        result.embedded_pdf = embed_cfg.local_embedded_pdf
        self._post_op(success=True, cfg=embed_cfg)
        return result

    # ── Individual stage methods ──────────────────────────────────────────────

    def extract(self, pdf_path: str, global_json_path: str) -> SDKResult:
        """Run only the extract stage — identifies form fields in the PDF."""
        _validate_pdf(pdf_path)
        _validate_json(global_json_path, "Global JSON schema")
        handle_extract, _, _, _, SDKStorageConfig, _ = _import_mapper_internals()
        cfg = self._make_embed_config(pdf_path, global_json_path, SDKStorageConfig)
        start = time.time()
        raw = self._run(handle_extract(cfg))
        return SDKResult.from_operation({
            "status": raw.get("status", "error"),
            "execution_time": time.time() - start,
            "pipeline_results": {"extract": raw},
            "error": raw.get("error"),
        })

    def map(self, pdf_path: str, global_json_path: str) -> SDKResult:
        """
        Run only the map stage — LLM semantic mapping of fields to data keys.

        Requires extract to have already run.  Uses both LLMs when
        ``use_second_mapper=True``.
        """
        _validate_pdf(pdf_path)
        _validate_json(global_json_path, "Global JSON schema")
        _, handle_map, _, _, SDKStorageConfig, _ = _import_mapper_internals()
        cfg = self._make_embed_config(pdf_path, global_json_path, SDKStorageConfig)
        start = time.time()
        raw = self._run(handle_map(cfg, self._build_mapping_config()))
        return SDKResult.from_operation({
            "status": raw.get("status", "error"),
            "execution_time": time.time() - start,
            "pipeline_results": {"map": raw},
            "error": raw.get("error"),
        })

    def embed(self, pdf_path: str, global_json_path: str) -> SDKResult:
        """Run only the embed stage — writes field metadata into the PDF via Java."""
        _validate_pdf(pdf_path)
        _validate_json(global_json_path, "Global JSON schema")
        _, _, handle_embed, _, SDKStorageConfig, _ = _import_mapper_internals()
        cfg = self._make_embed_config(pdf_path, global_json_path, SDKStorageConfig)
        start = time.time()
        raw = self._run(handle_embed(cfg))
        return SDKResult.from_operation({
            "status": raw.get("status", "error"),
            "execution_time": time.time() - start,
            "pipeline_results": {"embed": raw},
            "error": raw.get("error"),
        })

    # ── Config building ───────────────────────────────────────────────────────

    def _build_mapping_config(self) -> dict:
        """
        Build the mapping_config dict passed to handle_map_operation.

        Priority (highest wins):
          1. Constructor overrides (llm_model=, confidence_threshold=, …)
          2. config.ini [mapping] section
          3. config.ini [headers] section (merged in for second-mapper params)

        Raises ConfigurationError if no llm_model can be resolved.
        """
        try:
            _, _, _, _, _, IniConfigLoader = _import_mapper_internals()
            loader = IniConfigLoader(self._config_path)
            cfg = loader.get_mapping_config()
            # Merge headers config so handle_map_operation sees headers_llm_model etc.
            headers = loader.get_section("headers")
            for k, v in headers.items():
                cfg.setdefault(k, v)
        except ConfigurationError:
            raise
        except Exception:
            cfg = {}

        # Apply constructor overrides — they always win
        cfg.update(self._overrides)

        if not cfg.get("llm_model"):
            raise ConfigurationError(
                "No llm_model configured. Set it in config.ini [mapping] "
                "or pass llm_model= to PDFMapper()."
            )

        return cfg

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _make_embed_config(self, pdf_path: str, global_json_path: str, SDKStorageConfig):
        """Create an SDKStorageConfig for the embed pipeline (global JSON → map stage)."""
        cfg = SDKStorageConfig(
            pdf_path=pdf_path,
            global_json_path=global_json_path,
            output_dir=self._output_dir,
        )
        self._session_dirs.add(cfg.base_dir)
        return cfg

    def _make_fill_config(self, pdf_path: str, input_json_path: str, SDKStorageConfig):
        """Create an SDKStorageConfig for the fill pipeline (user data → fill stage)."""
        cfg = SDKStorageConfig(
            pdf_path=pdf_path,
            input_json_path=input_json_path,
            output_dir=self._output_dir,
        )
        self._session_dirs.add(cfg.base_dir)
        return cfg

    def _fail(self, error: str, cfg, elapsed: float) -> SDKResult:
        self._post_op(success=False, cfg=cfg)
        return SDKResult.failure(error, execution_time=elapsed)

    def _post_op(self, success: bool, cfg) -> None:
        """Apply per-call cleanup policy."""
        if (
            self._cleanup is True
            or (self._cleanup == "on_success" and success)
            or (self._cleanup == "on_error" and not success)
        ):
            out = getattr(cfg, "base_dir", None)
            if out and os.path.isdir(out):
                shutil.rmtree(out, ignore_errors=True)
                self._session_dirs.discard(out)

    @staticmethod
    def _run(coro):
        return asyncio.run(coro)

    def __repr__(self) -> str:
        model = self._overrides.get("llm_model", "<from config.ini>")
        return (
            f"PDFMapper("
            f"model={model!r}, "
            f"config={self._config_path!r}, "
            f"cleanup={self._cleanup!r})"
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _validate_pdf(pdf_path: str) -> None:
    if not os.path.exists(pdf_path):
        raise ConfigurationError(f"PDF not found: {pdf_path!r}")


def _validate_json(json_path: str, label: str = "Data JSON") -> None:
    if not os.path.exists(json_path):
        raise ConfigurationError(f"{label} not found: {json_path!r}")
