"""
StorageConfig — reads MAPPER_* env vars for storage base paths.

Replaces the [local]/[aws]/[azure]/[gcp] + [file_naming] + [paths] sections
in config.ini.  All storage location is now runtime config (env vars injected
via Docker .env) instead of build-time config (baked into the image).

Usage:
    from src.storage.storage_config import get_storage_config
    sc = get_storage_config()
    sc.input_path("1", "1", "100", "input.pdf")
    # → /app/data/input/1/1/100/input.pdf  (local)
    # → s3://bucket/prefix/input/1/1/100/input.pdf  (aws)
"""

import os
import logging
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class StorageConfig:
    """
    Provides base-path resolution from MAPPER_* environment variables.

    Env vars (all optional — defaults work for the standard Docker setup):
        MAPPER_STORAGE          local | aws | azure | gcp  (default: local)

        # Local
        MAPPER_INPUT_PATH       base dir for input files    (default: /app/data/input)
        MAPPER_OUTPUT_PATH      base dir for output files   (default: /app/data/output)
        MAPPER_CACHE_PATH       base dir for cache files    (default: /app/data/cache)
        MAPPER_PROCESSING_PATH  base dir for temp files     (default: /tmp/processing)

        # AWS S3  (also reads AWS_S3_BUCKET as fallback for MAPPER_S3_BUCKET)
        MAPPER_S3_BUCKET        S3 bucket name
        MAPPER_S3_PREFIX        prefix inside bucket        (default: pdf-autofiller)

        # Azure Blob  (also reads AZURE_STORAGE_CONTAINER as fallback)
        MAPPER_AZURE_CONTAINER  container name
        MAPPER_AZURE_PREFIX     prefix inside container     (default: pdf-autofiller)

        # GCP Cloud Storage  (also reads GCP_STORAGE_BUCKET as fallback)
        MAPPER_GCS_BUCKET       GCS bucket name
        MAPPER_GCS_PREFIX       prefix inside bucket        (default: pdf-autofiller)
    """

    def __init__(self):
        self.storage_type = (
            os.environ.get("MAPPER_STORAGE")
            or os.environ.get("CLOUD_PROVIDER", "local")
        ).lower()

        self._backend = None

        if self.storage_type == "aws":
            bucket = (
                os.environ.get("MAPPER_S3_BUCKET")
                or os.environ.get("AWS_S3_BUCKET", "")
            )
            prefix = os.environ.get("MAPPER_S3_PREFIX", "pdf-autofiller").rstrip("/")
            self._input_base      = f"s3://{bucket}/{prefix}/input"
            self._output_base     = f"s3://{bucket}/{prefix}/output"
            self._cache_base      = f"s3://{bucket}/{prefix}/cache"
            self._processing_base = os.environ.get("MAPPER_PROCESSING_PATH", "/tmp/processing")

        elif self.storage_type == "azure":
            container = (
                os.environ.get("MAPPER_AZURE_CONTAINER")
                or os.environ.get("AZURE_STORAGE_CONTAINER", "")
            )
            prefix = os.environ.get("MAPPER_AZURE_PREFIX", "pdf-autofiller").rstrip("/")
            self._input_base      = f"azure://{container}/{prefix}/input"
            self._output_base     = f"azure://{container}/{prefix}/output"
            self._cache_base      = f"azure://{container}/{prefix}/cache"
            self._processing_base = os.environ.get("MAPPER_PROCESSING_PATH", "/tmp/processing")

        elif self.storage_type == "gcp":
            bucket = (
                os.environ.get("MAPPER_GCS_BUCKET")
                or os.environ.get("GCP_STORAGE_BUCKET", "")
            )
            prefix = os.environ.get("MAPPER_GCS_PREFIX", "pdf-autofiller").rstrip("/")
            self._input_base      = f"gs://{bucket}/{prefix}/input"
            self._output_base     = f"gs://{bucket}/{prefix}/output"
            self._cache_base      = f"gs://{bucket}/{prefix}/cache"
            self._processing_base = os.environ.get("MAPPER_PROCESSING_PATH", "/tmp/processing")

        else:  # local (default)
            self._input_base      = os.environ.get("MAPPER_INPUT_PATH",      "/app/data/input")
            self._output_base     = os.environ.get("MAPPER_OUTPUT_PATH",     "/app/data/output")
            self._cache_base      = os.environ.get("MAPPER_CACHE_PATH",      "/app/data/cache")
            self._processing_base = os.environ.get("MAPPER_PROCESSING_PATH", "/tmp/processing")

        logger.debug(
            f"StorageConfig: type={self.storage_type} "
            f"input={self._input_base} output={self._output_base}"
        )

    # ── Backend ──────────────────────────────────────────────────────────────

    @property
    def backend(self):
        """Lazy-loaded storage backend (local/aws/azure/gcp)."""
        if self._backend is None:
            from src.storage.backends.factory import get_storage_backend
            self._backend = get_storage_backend(self.storage_type)
        return self._backend

    # ── Path builders ─────────────────────────────────────────────────────────

    def input_path(self, uid, sid, pid, filename: str) -> str:
        """Full path for an input file: {input_base}/{uid}/{sid}/{pid}/{filename}"""
        return f"{self._input_base}/{uid}/{sid}/{pid}/{filename}"

    def output_path(self, uid, sid, pid, filename: str) -> str:
        """Full path for an output file: {output_base}/{uid}/{sid}/{pid}/{filename}
        Creates parent directories automatically for local storage."""
        path = f"{self._output_base}/{uid}/{sid}/{pid}/{filename}"
        if not path.startswith(("s3://", "azure://", "gs://")):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def cache_path(self, filename: str) -> str:
        """Full path for a cache file in the configured backend (may be a cloud URI)."""
        path = f"{self._cache_base}/{filename}"
        if not path.startswith(("s3://", "azure://", "gs://")):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def local_cache_path(self, filename: str) -> str:
        """
        Local filesystem path for a cache file — ALWAYS local, regardless of storage backend.

        The hash registry is a server-side optimisation file that must be readable
        with normal file I/O (os.path.exists, open, json.load).  Cloud URIs are not
        valid here.  The local path is derived from:
          1. config.ini  [general] cache_registry_path  (parent dir, stripped of filename)
          2. env var     MAPPER_CACHE_PATH
          3. default     /app/data/cache
        """
        from src.core.config import settings
        # Use settings.cache_registry_path (from config.ini) if it's a local path
        cfg_path = getattr(settings, "cache_registry_path", "")
        if cfg_path and not cfg_path.startswith(("s3://", "azure://", "gs://")):
            # Use the directory from config.ini + requested filename
            local_base = os.path.dirname(cfg_path)
        else:
            local_base = os.environ.get("MAPPER_CACHE_PATH", "/app/data/cache")
        path = os.path.join(local_base, filename)
        os.makedirs(local_base, exist_ok=True)
        return path

    def new_processing_dir(self) -> str:
        """
        Create and return a fresh isolated temp directory for one request.
        Each call gets a unique UUID sub-directory so concurrent jobs never collide.
        """
        path = os.path.join(self._processing_base, str(uuid4()))
        os.makedirs(path, exist_ok=True)
        return path

    def processing_path(self, job_dir: str, filename: str) -> str:
        """Path for a temp file inside an existing job directory."""
        return os.path.join(job_dir, filename)


# ── Singleton ─────────────────────────────────────────────────────────────────

_storage_config: Optional[StorageConfig] = None


def get_storage_config() -> StorageConfig:
    """Return the process-level StorageConfig singleton."""
    global _storage_config
    if _storage_config is None:
        _storage_config = StorageConfig()
    return _storage_config


def reset_storage_config() -> None:
    """Reset the singleton (useful in tests or after env changes)."""
    global _storage_config
    _storage_config = None
    # Also reset backend cache so it's rebuilt with the new config
    try:
        from src.storage.backends.factory import clear_cache
        clear_cache()
    except ImportError:
        pass
