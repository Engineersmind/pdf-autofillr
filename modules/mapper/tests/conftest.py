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
    accidentally reads real AWS/Azure credentials or production paths
    from the shell environment.  Restores the original environment
    afterwards.
    """
    original_env = os.environ.copy()

    os.environ.setdefault("ENVIRONMENT", "test")
    os.environ.setdefault("LOCAL_WORKSPACE", str(tmp_path))
    os.environ.setdefault("AWS_REGION", "us-east-1")
    os.environ.setdefault("S3_BUCKET", "test-bucket")

    yield

    os.environ.clear()
    os.environ.update(original_env)
