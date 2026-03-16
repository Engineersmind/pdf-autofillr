"""
PDF Autofiller SDK — Result Object

SDKResult is returned by every PDFMapper method.  It provides a clean,
inspectable surface over the raw dict that the internal operations return.

Example usage::

    result = mapper.process("form.pdf", "data.json")

    if result.ok:
        result.save("filled_application.pdf")
        print(f"Mapped {result.total_fields} fields at {result.confidence:.0%} confidence")
    else:
        print(f"Failed: {result.error}")

    # Inspect individual field mappings
    for field_id, key in result.mapping.items():
        print(f"  field {field_id} → {key}")
"""

import shutil
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Any


@dataclass
class StageResult:
    """
    Result from a single pipeline stage (extract / map / embed / fill).

    Attributes:
        stage:          Name of the stage ("extract", "map", "embed", "fill").
        status:         "success" or "error".
        output_file:    Local path to the stage's primary output file, or None.
        execution_time: Wall-clock seconds the stage took.
        error:          Error message if status == "error", else None.
        meta:           Any extra data the stage returned (token counts, etc.).
    """

    stage: str
    status: str
    output_file: Optional[str] = None
    execution_time: float = 0.0
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "success"


@dataclass
class SDKResult:
    """
    Result returned by PDFMapper.process() and individual stage methods.

    Attributes:
        status:         "success" or "error".
        filled_pdf:     Local path to the final filled PDF (process() only).
        embedded_pdf:   Local path to the embedded PDF produced by
                        make_embed_file() (extract+map+embed pipeline).
        mapping:        Dict mapping internal field IDs to input-data keys,
                        e.g. ``{"1": "firstName", "2": "lastName"}``.
        confidence:     Average confidence score across all mapped fields (0–1).
        total_fields:   Total number of form fields found in the PDF.
        mapped_fields:  Number of fields successfully mapped (confidence above
                        threshold).
        execution_time: Total wall-clock seconds for the full pipeline.
        error:          Top-level error message if status == "error".
        stages:         Per-stage results (extract / map / embed / fill).
    """

    status: str
    filled_pdf: Optional[str] = None
    embedded_pdf: Optional[str] = None
    mapping: Dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    total_fields: int = 0
    mapped_fields: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    stages: Dict[str, StageResult] = field(default_factory=dict)

    # ── Core helpers ──────────────────────────────────────────────────────────

    @property
    def ok(self) -> bool:
        """True when the operation completed successfully."""
        return self.status == "success"

    def save(self, destination: str) -> str:
        """
        Copy the filled PDF to *destination*.

        Args:
            destination: Target file path (directories must already exist,
                         or use a plain filename in the current directory).

        Returns:
            The absolute path of the saved file.

        Raises:
            ValueError:  If no filled PDF is available (check ``result.ok``).
            FileNotFoundError: If the internal filled PDF has been deleted.
        """
        if not self.filled_pdf:
            raise ValueError(
                "No filled PDF available — operation may have failed. "
                f"status={self.status!r}, error={self.error!r}"
            )
        if not os.path.exists(self.filled_pdf):
            raise FileNotFoundError(
                f"Filled PDF no longer exists at {self.filled_pdf!r}. "
                "The output_dir may have been cleaned up."
            )
        destination = os.path.abspath(destination)
        shutil.copy2(self.filled_pdf, destination)
        return destination

    # ── Display helpers ───────────────────────────────────────────────────────

    def __str__(self) -> str:
        if self.ok:
            return (
                f"SDKResult(status=success, "
                f"fields={self.mapped_fields}/{self.total_fields}, "
                f"confidence={self.confidence:.0%}, "
                f"time={self.execution_time:.1f}s)"
            )
        return f"SDKResult(status=error, error={self.error!r})"

    def __repr__(self) -> str:
        return self.__str__()

    # ── Internal factory ──────────────────────────────────────────────────────

    @classmethod
    def from_operation(cls, raw: Dict[str, Any], filled_pdf: Optional[str] = None) -> "SDKResult":
        """
        Build an SDKResult from the raw dict returned by handle_* operations.

        Args:
            raw:        The dict returned by e.g. handle_make_embed_file_operation.
            filled_pdf: Path to the filled PDF (may be inside raw or passed explicitly).

        Returns:
            SDKResult instance.
        """
        status = raw.get("status", "error")
        error = raw.get("error") or raw.get("message")

        # Resolve filled PDF path — look in common locations
        filled = (
            filled_pdf
            or raw.get("filled_pdf")
            or raw.get("output_file")
            or _dig(raw, "pipeline_results", "fill", "output_file")
        )

        # Extract mapping dict — may be nested under pipeline_results.map
        mapping_raw = (
            raw.get("mapping")
            or _dig(raw, "pipeline_results", "map", "mapping")
            or {}
        )
        # Normalise: keep only {field_id: key_name} pairs, drop None values
        mapping = {
            str(k): v
            for k, v in mapping_raw.items()
            if v is not None
        }

        # Confidence — average across mapped fields if available
        confidence = float(
            raw.get("confidence")
            or _dig(raw, "pipeline_results", "map", "confidence")
            or 0.0
        )

        total_fields = int(
            raw.get("total_fields")
            or _dig(raw, "pipeline_results", "map", "total_fields_mapped")
            or len(mapping_raw)
        )
        mapped_fields = int(
            raw.get("mapped_fields")
            or _dig(raw, "pipeline_results", "map", "total_fields_mapped")
            or len(mapping)
        )

        execution_time = float(raw.get("execution_time") or 0.0)

        # Per-stage breakdown
        stages: Dict[str, StageResult] = {}
        pipeline = raw.get("pipeline_results") or {}
        for stage_name, stage_raw in pipeline.items():
            if isinstance(stage_raw, dict):
                stages[stage_name] = StageResult(
                    stage=stage_name,
                    status=stage_raw.get("status", "unknown"),
                    output_file=stage_raw.get("output_file"),
                    execution_time=float(stage_raw.get("execution_time", 0.0)),
                    error=stage_raw.get("error"),
                    meta={k: v for k, v in stage_raw.items()
                          if k not in ("status", "output_file", "execution_time", "error")},
                )

        return cls(
            status=status,
            filled_pdf=filled,
            mapping=mapping,
            confidence=confidence,
            total_fields=total_fields,
            mapped_fields=mapped_fields,
            execution_time=execution_time,
            error=error,
            stages=stages,
        )

    @classmethod
    def failure(cls, error: str, execution_time: float = 0.0) -> "SDKResult":
        """Create a failed SDKResult with just an error message."""
        return cls(status="error", error=error, execution_time=execution_time)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dig(d: dict, *keys) -> Any:
    """Safely traverse nested dicts — returns None if any key is missing."""
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d
