"""
PathResolver - generates all file paths from job parameters.

Single source of truth for every filename in the pipeline.
Delegates base-path resolution to StorageConfig (reads MAPPER_* env vars).

Adding a new pipeline file = add one method here, nowhere else.
"""

import os


# ── Filename constants ─────────────────────────────────────────────────────────
# Changing a filename? Update it here — one place, all paths follow.

_INPUT_PDF       = "input.pdf"
_GLOBAL_JSON     = "global_schema.json"
_INPUT_JSON      = "input_data.json"

_EXTRACTED_JSON  = "extracted.json"
_MAPPED_JSON     = "mapped.json"
_RADIO_JSON      = "radio_groups.json"
_EMBEDDED_PDF    = "embedded.pdf"
_FILLED_PDF      = "filled.pdf"

_SEMANTIC_MAP    = "semantic_mapping.json"
_HEADERS_FIELDS  = "headers_with_fields.json"
_FINAL_FIELDS    = "final_form_fields.json"
_HEADER_FILE     = "header_file.json"
_SECTION_FILE    = "section_file.json"
_JAVA_MAPPING    = "java_mapping.json"
_FINAL_PRED      = "final_predictions.json"
_LLM_PRED        = "llm_predictions.json"
_RAG_PRED        = "rag_predictions.json"

_CACHE_REGISTRY  = "hash_registry.json"


class PathResolver:
    """
    Generates remote (source storage) and local (processing) paths
    for every file in the pipeline.

    Remote paths  → source storage (S3, Azure, GCS, or /app/data/ for local)
    Local paths   → /tmp/processing/<uuid>/ for in-flight processing
    """

    def __init__(self, storage_config):
        self._sc = storage_config

    # ── Remote input paths ───────────────────────────────────────────────────

    def remote_input_pdf(self, uid, sid, pid) -> str:
        return self._sc.input_path(uid, sid, pid, _INPUT_PDF)

    def remote_global_json(self, uid, sid, pid) -> str:
        """Keys-only schema used by the map phase (make_embed_file pipeline)."""
        return self._sc.input_path(uid, sid, pid, _GLOBAL_JSON)

    def remote_input_json(self, uid, sid, pid) -> str:
        """Per-user data used by the fill phase."""
        return self._sc.input_path(uid, sid, pid, _INPUT_JSON)

    # ── Remote output paths (where results are persisted) ────────────────────

    def remote_extracted(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _EXTRACTED_JSON)

    def remote_mapped(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _MAPPED_JSON)

    def remote_radio(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _RADIO_JSON)

    def remote_embedded(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _EMBEDDED_PDF)

    def remote_filled(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _FILLED_PDF)

    def remote_semantic_mapping(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _SEMANTIC_MAP)

    def remote_headers_with_fields(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _HEADERS_FIELDS)

    def remote_final_form_fields(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _FINAL_FIELDS)

    def remote_header_file(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _HEADER_FILE)

    def remote_section_file(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _SECTION_FILE)

    def remote_java_mapping(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _JAVA_MAPPING)

    def remote_final_predictions(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _FINAL_PRED)

    def remote_llm_predictions(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _LLM_PRED)

    def remote_rag_predictions(self, uid, sid, pid) -> str:
        return self._sc.output_path(uid, sid, pid, _RAG_PRED)

    def remote_cache_registry(self, uid, sid, pid) -> str:
        """Destination path for uploading the cache registry (may be a cloud URI)."""
        return self._sc.cache_path(_CACHE_REGISTRY)

    def local_cache_registry_path(self) -> str:
        """Always-local path for reading/writing the cache registry with normal file I/O."""
        return self._sc.local_cache_path(_CACHE_REGISTRY)

    # ── Local processing paths (all under processing_dir) ────────────────────

    def local_paths(self, uid, sid, pid, processing_dir: str) -> dict:
        """Return all local processing paths for a job."""
        p = lambda f: os.path.join(processing_dir, f)
        return {
            "processing_input_pdf":    p(_INPUT_PDF),
            "processing_global_json":  p(_GLOBAL_JSON),
            "processing_input_json":   p(_INPUT_JSON),
            "extracted_json":          p(_EXTRACTED_JSON),
            "mapped_json":             p(_MAPPED_JSON),
            "radio_groups_json":       p(_RADIO_JSON),
            "embedded_pdf":            p(_EMBEDDED_PDF),
            "filled_pdf":              p(_FILLED_PDF),
            "semantic_mapping":        p(_SEMANTIC_MAP),
            "headers_with_fields":     p(_HEADERS_FIELDS),
            "final_form_fields":       p(_FINAL_FIELDS),
            "header_file":             p(_HEADER_FILE),
            "section_file":            p(_SECTION_FILE),
            "java_mapping":            p(_JAVA_MAPPING),
            "final_predictions":       p(_FINAL_PRED),
            "llm_predictions":         p(_LLM_PRED),
            "rag_predictions":         p(_RAG_PRED),
        }
