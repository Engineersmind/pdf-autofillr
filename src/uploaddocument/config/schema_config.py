"""SchemaConfig — loads form_keys.json for LLM extraction."""
from __future__ import annotations
import json
from pathlib import Path


class SchemaConfig:
    """
    Loads and validates the extraction schema (form_keys.json).
    Same naming convention as FormConfig in finform-sdk.
    """

    def __init__(self, form_keys: dict):
        if not isinstance(form_keys, dict):
            raise ValueError("form_keys must be a dict")
        self.form_keys = form_keys

    @classmethod
    def from_directory(cls, config_dir: str) -> "SchemaConfig":
        """Load form_keys.json from a local directory."""
        path = Path(config_dir) / "form_keys.json"
        if not path.exists():
            raise FileNotFoundError(
                f"form_keys.json not found at {path}\n"
                f"Copy config_samples/form_keys.json into {config_dir}/"
            )
        with open(path, "r", encoding="utf-8") as f:
            return cls(form_keys=json.load(f))

    @classmethod
    def from_s3(cls, s3_uri: str, region: str = "us-east-1") -> "SchemaConfig":
        """Load form_keys.json directly from an S3 URI."""
        try:
            import boto3
        except ImportError:
            raise ImportError("boto3 required: pip install upload-document-sdk[s3]")
        s3 = boto3.client("s3", region_name=region)
        bucket, key = s3_uri.replace("s3://", "").split("/", 1)
        resp = s3.get_object(Bucket=bucket, Key=key)
        return cls(form_keys=json.loads(resp["Body"].read()))

    @classmethod
    def from_storage(cls, storage) -> "SchemaConfig":
        """Load schema from any StorageBackend."""
        return cls(form_keys=storage.load_config("form_keys.json"))
