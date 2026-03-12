# chatbot/storage/factory.py
"""StorageFactory — creates the correct backend from config."""
from __future__ import annotations
import os
from chatbot.storage.base import StorageBackend


class StorageFactory:
    @staticmethod
    def create(storage_type: str = None, **kwargs) -> StorageBackend:
        storage_type = storage_type or os.getenv("chatbot_STORAGE", "local")
        if storage_type == "local":
            from chatbot.storage.local_storage import LocalStorage
            return LocalStorage(
                data_path=kwargs.get("data_path", os.getenv("chatbot_DATA_PATH", "./chatbot_data")),
                config_path=kwargs.get("config_path", os.getenv("chatbot_CONFIG_PATH", "./configs")),
            )
        elif storage_type == "s3":
            from chatbot.storage.s3_storage import S3Storage
            return S3Storage(
                output_bucket=kwargs.get("output_bucket", os.environ["AWS_OUTPUT_BUCKET"]),
                config_bucket=kwargs.get("config_bucket", os.environ["AWS_CONFIG_BUCKET"]),
                region=kwargs.get("region", os.getenv("AWS_REGION", "us-east-1")),
            )
        else:
            raise ValueError(f"Unknown storage type: {storage_type!r}. Use 'local' or 's3'.")
