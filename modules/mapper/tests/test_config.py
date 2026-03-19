"""
Tests for StorageConfig — path building from MAPPER_* env vars.
"""

import os
import pytest

from src.storage.storage_config import StorageConfig, get_storage_config, reset_storage_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sc(**overrides) -> StorageConfig:
    """Build a fresh StorageConfig with env vars already set by conftest."""
    reset_storage_config()
    for k, v in overrides.items():
        os.environ[k] = v
    sc = StorageConfig()
    reset_storage_config()  # leave singleton clean for next test
    return sc


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

class TestStorageType:
    def test_defaults_to_local(self, tmp_path):
        sc = _make_sc()
        assert sc.storage_type == "local"

    def test_mapper_storage_env_wins(self, tmp_path):
        sc = _make_sc(MAPPER_STORAGE="aws",
                      MAPPER_S3_BUCKET="my-bucket",
                      AWS_ACCESS_KEY_ID="key", AWS_SECRET_ACCESS_KEY="secret")
        assert sc.storage_type == "aws"

    def test_cloud_provider_fallback(self, tmp_path):
        os.environ.pop("MAPPER_STORAGE", None)
        sc = _make_sc(CLOUD_PROVIDER="azure",
                      MAPPER_AZURE_CONTAINER="ctr",
                      AZURE_STORAGE_CONNECTION_STRING="conn")
        assert sc.storage_type == "azure"


# ---------------------------------------------------------------------------
# Local path building
# ---------------------------------------------------------------------------

class TestLocalPaths:
    def test_input_path_structure(self, tmp_path):
        sc = _make_sc()
        p = sc.input_path("1", "sess1", "100", "input.pdf")
        assert p == str(tmp_path / "input" / "1" / "sess1" / "100" / "input.pdf")

    def test_output_path_structure(self, tmp_path):
        sc = _make_sc()
        p = sc.output_path("1", "sess1", "100", "extracted.json")
        assert p == str(tmp_path / "output" / "1" / "sess1" / "100" / "extracted.json")

    def test_output_path_creates_parent_dir(self, tmp_path):
        sc = _make_sc()
        p = sc.output_path("1", "sess1", "100", "filled.pdf")
        assert os.path.isdir(os.path.dirname(p))

    def test_cache_path_structure(self, tmp_path):
        sc = _make_sc()
        p = sc.cache_path("hash_registry.json")
        assert p == str(tmp_path / "cache" / "hash_registry.json")

    def test_processing_dir_is_unique(self, tmp_path):
        sc = _make_sc()
        d1 = sc.new_processing_dir()
        d2 = sc.new_processing_dir()
        assert d1 != d2
        assert os.path.isdir(d1)
        assert os.path.isdir(d2)

    def test_processing_path_joins_correctly(self, tmp_path):
        sc = _make_sc()
        job_dir = sc.new_processing_dir()
        p = sc.processing_path(job_dir, "extracted.json")
        assert p == os.path.join(job_dir, "extracted.json")


# ---------------------------------------------------------------------------
# Cloud path building
# ---------------------------------------------------------------------------

class TestCloudPaths:
    def test_s3_paths_use_bucket_and_prefix(self):
        sc = _make_sc(MAPPER_STORAGE="aws",
                      MAPPER_S3_BUCKET="my-bucket",
                      MAPPER_S3_PREFIX="pdf-autofiller",
                      AWS_ACCESS_KEY_ID="k", AWS_SECRET_ACCESS_KEY="s")
        assert sc.input_path("1", "s", "100", "input.pdf") == \
            "s3://my-bucket/pdf-autofiller/input/1/s/100/input.pdf"
        assert sc.output_path("1", "s", "100", "filled.pdf") == \
            "s3://my-bucket/pdf-autofiller/output/1/s/100/filled.pdf"
        assert sc.cache_path("hash_registry.json") == \
            "s3://my-bucket/pdf-autofiller/cache/hash_registry.json"

    def test_azure_paths_use_container_and_prefix(self):
        sc = _make_sc(MAPPER_STORAGE="azure",
                      MAPPER_AZURE_CONTAINER="my-container",
                      MAPPER_AZURE_PREFIX="pdf-autofiller",
                      AZURE_STORAGE_CONNECTION_STRING="conn")
        assert sc.input_path("1", "s", "100", "input.pdf") == \
            "azure://my-container/pdf-autofiller/input/1/s/100/input.pdf"

    def test_gcp_paths_use_bucket_and_prefix(self):
        sc = _make_sc(MAPPER_STORAGE="gcp",
                      MAPPER_GCS_BUCKET="my-bucket",
                      MAPPER_GCS_PREFIX="pdf-autofiller",
                      GOOGLE_APPLICATION_CREDENTIALS="/creds.json",
                      GOOGLE_CLOUD_PROJECT="proj")
        assert sc.input_path("1", "s", "100", "input.pdf") == \
            "gs://my-bucket/pdf-autofiller/input/1/s/100/input.pdf"

    def test_cloud_output_path_does_not_mkdir(self):
        """output_path must not call makedirs for cloud URIs."""
        sc = _make_sc(MAPPER_STORAGE="aws",
                      MAPPER_S3_BUCKET="b",
                      AWS_ACCESS_KEY_ID="k", AWS_SECRET_ACCESS_KEY="s")
        # Should not raise even though the "directory" doesn't exist
        p = sc.output_path("1", "s", "100", "filled.pdf")
        assert p.startswith("s3://")


# ---------------------------------------------------------------------------
# Singleton behaviour
# ---------------------------------------------------------------------------

class TestSingleton:
    def test_get_storage_config_returns_same_instance(self, tmp_path):
        reset_storage_config()
        a = get_storage_config()
        b = get_storage_config()
        assert a is b

    def test_reset_clears_singleton(self, tmp_path):
        reset_storage_config()
        a = get_storage_config()
        reset_storage_config()
        b = get_storage_config()
        assert a is not b
