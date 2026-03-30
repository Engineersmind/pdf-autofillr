# modules3/mapper/src/pdf_autofillr_mapper/inprocess_filler.py
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)
"""
InProcessMapperFiller
=====================
Runs the full mapper pipeline (Extract -> Map -> Embed -> Fill) in-process.

Used by MapperPDFFiller when MAPPER_API_URL is NOT set.
No HTTP. No separate server needed.

Output layout:
    {data_path}/{user_id}/sessions/{session_id}/mapper/
        blank_form_extracted.json
        blank_form_mapped.json
        blank_form_radio.json
        blank_form_embedded.pdf

    {data_path}/{user_id}/sessions/{session_id}/
        filled.pdf
"""

class InProcessMapperFiller:

    def __init__(self, mapper_config=None, config_dir: Optional[str] = None):
        from pdf_autofillr_mapper.config.mapper_config import MapperConfig
        from pdf_autofillr_mapper.orchestrator import PDFPipeline

        self._config_dir = config_dir or os.getenv("chatbot_CONFIG_PATH", "./configs")

        if mapper_config is None:
            ini_path = Path(self._config_dir) / "mapper_config.ini"
            if ini_path.exists():
                mapper_config = MapperConfig.from_directory(self._config_dir)
                logger.info("InProcessMapperFiller: loaded config from %s", ini_path)
            else:
                mapper_config = MapperConfig.from_env()
                logger.info("InProcessMapperFiller: no mapper_config.ini, using env vars")

        self._mapper_config = mapper_config
        self._pipeline = PDFPipeline(mapper_config=mapper_config)

    def prepare_document(self, pdf_path: str, investor_type: str,
                         session_dir: Optional[str] = None) -> str:
        """
        Run Extract + Map + Embed on the blank PDF.

        Args:
            pdf_path:      Path to the blank input PDF.
            investor_type: Investor type string (e.g. "Individual").
            session_dir:   Directory for intermediate files.
                           Passed by workflow.py as
                           {data_path}/{user_id}/sessions/{session_id}/mapper/
                           When None, files land next to the input PDF.

        Returns:
            Path to the embedded PDF (used as doc_id).
        """
        import asyncio

        logger.info("InProcessMapperFiller.prepare_document: pdf=%s type=%s session_dir=%s",
                    pdf_path, investor_type, session_dir or "(next to pdf)")
        schema_path = self._get_form_keys_path()
        pdf_stem = Path(pdf_path).stem

        if session_dir:
            out_dir = Path(session_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = Path(pdf_path).parent

        async def _run():
            extract = await self._pipeline.extract(
                pdf_path=pdf_path,
                output_path=str(out_dir / f"{pdf_stem}_extracted.json"),
            )
            extracted_json = extract["output_file"]

            map_result = await self._pipeline.map(
                extracted_json_path=extracted_json,
                input_schema_path=schema_path,
                output_path=str(out_dir / f"{pdf_stem}_mapped.json"),
                radio_output_path=str(out_dir / f"{pdf_stem}_radio.json"),
            )
            mapping_json = map_result["output_files"]["mapping"]
            radio_json = map_result["output_files"]["radio_groups"]

            embed = await self._pipeline.embed(
                original_pdf_path=pdf_path,
                extracted_json_path=extracted_json,
                mapping_json_path=mapping_json,
                radio_json_path=radio_json,
                output_path=str(out_dir / f"{pdf_stem}_embedded.pdf"),
            )
            return embed["output_file"]

        return asyncio.run(_run())

    def check_document_ready(self, doc_id: str) -> bool:
        return Path(doc_id).exists()

    def fill_document(self, doc_id: str, data_flat: dict,
                      output_path: Optional[str] = None) -> Any:
        """
        Fill the embedded PDF with collected investor data.

        Args:
            doc_id:      Embedded PDF path from prepare_document().
            data_flat:   Flat dict of field values.
            output_path: Destination for filled PDF.
                         workflow.py passes
                         {data_path}/{user_id}/sessions/{session_id}/filled.pdf
                         When None, lands next to the embedded PDF.
        """
        import asyncio

        logger.info("InProcessMapperFiller.fill_document: doc_id=%s fields=%d output=%s",
                    doc_id, len(data_flat), output_path or "(next to embedded pdf)")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix="_fill_data.json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(data_flat, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name

        try:
            result = asyncio.run(
                self._pipeline.fill(
                    embedded_pdf_path=doc_id,
                    input_data_path=tmp_path,
                    output_path=output_path,
                )
            )
            logger.info("InProcessMapperFiller.fill_document: done -> %s", result.get("output_file"))
            return result
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def _get_form_keys_path(self) -> str:
        candidates = [
            Path(self._config_dir) / "form_keys.json",
            Path("configs") / "form_keys.json",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        raise FileNotFoundError(
            "form_keys.json not found. Looked in:\n"
            + "\n".join(f"  {p}" for p in candidates)
            + "\n\nRun copy_sample_configs() first, or set chatbot_CONFIG_PATH."
        )