"""StorageFactory — creates the correct backend from environment config."""
from __future__ import annotations
import os
from uploaddocument.storage.base import StorageBackend


class StorageFactory:
    @staticmethod
    def create(storage_type: str = None, **kwargs) -> StorageBackend:
        storage_type = storage_type or os.getenv("UPLOAD_DOC_STORAGE", "local")
        if storage_type == "local":
            from uploaddocument.storage.local_storage import LocalStorage
            return LocalStorage(
                data_path=kwargs.get("data_path", os.getenv("UPLOAD_DOC_DATA_PATH", "./uploaddoc_data")),
                config_path=kwargs.get("config_path", os.getenv("UPLOAD_DOC_CONFIG_PATH", "./configs")),
            )
        elif storage_type == "s3":
            from uploaddocument.storage.s3_storage import S3Storage
            return S3Storage(
                static_bucket=kwargs.get("static_bucket", os.environ["STATIC_BUCKET"]),
                output_bucket=kwargs.get("output_bucket", os.environ["OUTPUT_BUCKET"]),
                region=kwargs.get("region", os.getenv("AWS_REGION", "us-east-1")),
            )
        else:
            raise ValueError(f"Unknown storage type: {storage_type!r}. Use 'local' or 's3'.")
