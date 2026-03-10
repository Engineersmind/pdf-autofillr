"""S3Storage — uses your own S3 buckets."""
from __future__ import annotations
import json
from typing import Any, List, Optional
from uploaddocument.storage.base import StorageBackend

try:
    import boto3
    from botocore.exceptions import ClientError
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False


class S3Storage(StorageBackend):
    """
    Uses two S3 buckets:
      - static_bucket:  form_keys.json config (read-only)
      - output_bucket:  extraction results and logs (read/write)
    """

    def __init__(self, static_bucket: str, output_bucket: str, region: str = "us-east-1"):
        if not _BOTO3_AVAILABLE:
            raise ImportError("boto3 required: pip install upload-document-sdk[s3]")
        self.static_bucket = static_bucket
        self.output_bucket = output_bucket
        self.s3 = boto3.client("s3", region_name=region)

    def _get(self, bucket: str, key: str) -> Optional[Any]:
        try:
            resp = self.s3.get_object(Bucket=bucket, Key=key)
            return json.loads(resp["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            raise

    def _put(self, bucket: str, key: str, data: Any) -> bool:
        try:
            self.s3.put_object(
                Bucket=bucket, Key=key,
                Body=json.dumps(data, ensure_ascii=False, indent=2, default=str),
                ContentType="application/json",
            )
            return True
        except ClientError as e:
            print(f"❌ S3Storage put error {key}: {e}")
            return False

    def _sk(self, user_id, session_id, filename):
        return f"{user_id}/sessions/{session_id}/{filename}"

    def get_extraction_result(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "extraction_result.json"))

    def save_extraction_result(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "extraction_result.json"), data)

    def get_extraction_result_flat(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "extraction_result_flat.json"))

    def save_extraction_result_flat(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "extraction_result_flat.json"), data)

    def get_pdf_filling_logs(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "calling_filling_logs.json"))

    def save_pdf_filling_logs(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "calling_filling_logs.json"), data)

    def save_execution_logs(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "execution_logs.json"), data)

    def get_session_state(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "session_state.json"))

    def save_session_state(self, user_id, session_id, state):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "session_state.json"), state)

    def list_user_sessions(self, user_id):
        prefix = f"{user_id}/sessions/"
        try:
            resp = self.s3.list_objects_v2(Bucket=self.output_bucket, Prefix=prefix, Delimiter="/")
            return [p["Prefix"].replace(prefix, "").rstrip("/") for p in resp.get("CommonPrefixes", [])]
        except ClientError:
            return []

    def delete_session(self, user_id, session_id):
        prefix = f"{user_id}/sessions/{session_id}/"
        try:
            resp = self.s3.list_objects_v2(Bucket=self.output_bucket, Prefix=prefix)
            if "Contents" in resp:
                self.s3.delete_objects(
                    Bucket=self.output_bucket,
                    Delete={"Objects": [{"Key": o["Key"]} for o in resp["Contents"]]},
                )
            return True
        except ClientError as e:
            print(f"❌ S3Storage delete error: {e}")
            return False

    def load_config(self, filename: str) -> dict:
        data = self._get(self.static_bucket, filename)
        if data is None:
            raise FileNotFoundError(f"Config not found in S3: {self.static_bucket}/{filename}")
        return data
