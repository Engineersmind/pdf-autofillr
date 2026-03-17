# src/ragpdf/storage/factory.py
from ragpdf.storage.base import StorageBackend


class StorageFactory:
    """Create a storage backend from environment variables."""

    @staticmethod
    def create() -> StorageBackend:
        from ragpdf.config.settings import (
            RAGPDF_STORAGE, RAGPDF_DATA_PATH,
            RAGPDF_S3_BUCKET, RAGPDF_S3_REGION, RAGPDF_S3_PREFIX,
        )
        if RAGPDF_STORAGE == "s3":
            from ragpdf.storage.s3_storage import S3Storage
            return S3Storage(
                bucket=RAGPDF_S3_BUCKET,
                region=RAGPDF_S3_REGION,
                prefix=RAGPDF_S3_PREFIX,
            )
        from ragpdf.storage.local_storage import LocalStorage
        return LocalStorage(data_path=RAGPDF_DATA_PATH)
