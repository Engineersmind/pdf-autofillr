"""
Shared pytest configuration for mapper module tests.

Fixtures here apply to all test files automatically.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def setup_env_vars(tmp_path):
    """
    Inject dummy environment variables for every test so that no test
    accidentally reads real cloud credentials or production paths.
    Restores the original environment afterwards.
    """
    original_env = os.environ.copy()

    # Core identity
    os.environ.setdefault("ENVIRONMENT", "test")

    # Storage (MAPPER_* — used by StorageConfig)
    os.environ["MAPPER_STORAGE"] = "local"
    os.environ["MAPPER_INPUT_PATH"] = str(tmp_path / "input")
    os.environ["MAPPER_OUTPUT_PATH"] = str(tmp_path / "output")
    os.environ["MAPPER_CACHE_PATH"] = str(tmp_path / "cache")
    os.environ["MAPPER_PROCESSING_PATH"] = str(tmp_path / "processing")

    # Dummy cloud vars so backend credential checks don't fail if imported
    os.environ.setdefault("AWS_REGION", "us-east-1")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-key")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret")

    yield

    os.environ.clear()
    os.environ.update(original_env)

    # Reset the StorageConfig singleton so the next test gets fresh paths
    try:
        from src.storage.storage_config import reset_storage_config
        reset_storage_config()
    except ImportError:
        pass
