"""
PathResolver - generates all file paths from job parameters.

Single source of truth for every path in the pipeline.
Replaces the attribute-bag pattern on storage config objects.

All paths are derived from (user_id, session_id, pdf_doc_id) + config.ini.
Adding a new pipeline file = add one method here, nowhere else.
"""


class PathResolver:
    """
    Generates remote (source storage) and local (processing) paths
    for every file in the pipeline.

    Remote paths  → source storage (S3, Azure, GCS, or local output dir)
    Local paths   → /tmp/processing/ for in-flight processing
    """

    def __init__(self, file_config):
        self._cfg = file_config

    # ── Remote input paths ──────────────────────────────────────────────

    def remote_input_pdf(self, uid, sid, pid) -> str:
        return self._cfg.get_source_input_path('pdf', uid, sid, pid)

    def remote_input_json(self, uid, sid, pid) -> str:
        return self._cfg.get_source_input_path('json', uid, sid, pid)

    # ── Remote output paths (where results are persisted) ───────────────

    def remote_extracted(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('extracted_json', uid, sid, pid)

    def remote_mapped(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('mapped_json', uid, sid, pid)

    def remote_radio(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('radio_groups_json', uid, sid, pid)

    def remote_embedded(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('embedded_pdf', uid, sid, pid)

    def remote_filled(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('filled_pdf', uid, sid, pid)

    def remote_semantic_mapping(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('semantic_mapping_json', uid, sid, pid)

    def remote_headers_with_fields(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('headers_with_fields_json', uid, sid, pid)

    def remote_final_form_fields(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('final_form_fields_json', uid, sid, pid)

    def remote_header_file(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('header_file_json', uid, sid, pid)

    def remote_section_file(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('section_file_json', uid, sid, pid)

    def remote_java_mapping(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('java_mapping', uid, sid, pid)

    def remote_final_predictions(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('final_predictions', uid, sid, pid)

    def remote_llm_predictions(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('llm_predictions', uid, sid, pid)

    def remote_rag_predictions(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('rag_predictions', uid, sid, pid)

    def remote_cache_registry(self, uid, sid, pid) -> str:
        return self._cfg.get_source_output_path('cache_registry_json', uid, sid, pid)

    # ── Local processing paths (all under processing_dir) ───────────────

    def local_paths(self, uid, sid, pid, processing_dir: str = None) -> dict:
        """
        Return all local processing paths for a job.

        Args:
            processing_dir: Optional isolated directory (e.g. /tmp/processing/<uuid>).
                            If None, uses the value from config.ini.
                            Pass a unique path per request to prevent concurrent job collisions.
        """
        return self._cfg.get_all_processing_paths(uid, sid, pid, processing_dir)
