# chatbot/storage/s3_storage.py
"""
S3Storage — developer's own S3 buckets backend.
Identical file layout to LocalStorage.
"""
from __future__ import annotations

import json
from typing import Any, List, Optional

from chatbot.storage.base import StorageBackend

try:
    import boto3
    from botocore.exceptions import ClientError
    _BOTO3_AVAILABLE = True
except ImportError:
    _BOTO3_AVAILABLE = False


class S3Storage(StorageBackend):
    """
    Uses two S3 buckets:

    - ``output_bucket``: session data (read/write)
    - ``config_bucket``: form config files (read-only)

    AWS credentials via standard boto3 chain (env vars, ~/.aws/credentials, IAM role).
    """

    def __init__(
        self,
        output_bucket: str,
        config_bucket: str,
        region: str = "us-east-1",
    ):
        if not _BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3Storage. Install it with: pip install chatbot-sdk[s3]"
            )
        self.output_bucket = output_bucket
        self.config_bucket = config_bucket
        self.s3 = boto3.client("s3", region_name=region)

    # ── Helpers ────────────────────────────────────────────────────────

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
                Bucket=bucket,
                Key=key,
                Body=json.dumps(data, ensure_ascii=False, indent=2, default=str),
                ContentType="application/json",
            )
            return True
        except ClientError as e:
            print(f"❌ S3Storage put error {key}: {e}")
            return False

    # ── Key patterns ───────────────────────────────────────────────────

    def _sk(self, user_id: str, session_id: str, filename: str) -> str:
        return f"{user_id}/sessions/{session_id}/{filename}"

    def _uk(self, user_id: str, filename: str) -> str:
        return f"{user_id}/{filename}"

    # ── Session state ──────────────────────────────────────────────────

    def get_session_state(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "session_state.json"))

    def save_session_state(self, user_id, session_id, state):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "session_state.json"), state)

    # ── User integrated info ───────────────────────────────────────────

    def get_user_integrated_info(self, user_id):
        data = self._get(self.output_bucket, self._uk(user_id, "user_integrated_information.json"))
        return data.get("data", data) if isinstance(data, dict) else data

    def save_user_integrated_info(self, user_id, data):
        return self._put(self.output_bucket, self._uk(user_id, "user_integrated_information.json"), {"data": data})

    # ── Final output ───────────────────────────────────────────────────

    def get_final_output(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "final_output.json"))

    def save_final_output(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "final_output.json"), data)

    def get_final_output_flat(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "final_output_flat.json"))

    def save_final_output_flat(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "final_output_flat.json"), data)

    # ── Session history ────────────────────────────────────────────────

    def get_session_history(self, user_id):
        return self._get(self.output_bucket, self._uk(user_id, "session_history.json"))

    def save_session_history(self, user_id, history):
        return self._put(self.output_bucket, self._uk(user_id, "session_history.json"), history)

    # ── Logs ───────────────────────────────────────────────────────────

    def save_conversation_log(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "conversation_log.json"), data)

    def save_debug_conversation(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "debug_conversation.json"), data)

    def get_debug_conversation(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "debug_conversation.json"))

    def get_pdf_filling_logs(self, user_id, session_id):
        return self._get(self.output_bucket, self._sk(user_id, session_id, "calling_filling_logs.json"))

    def save_pdf_filling_logs(self, user_id, session_id, data):
        return self._put(self.output_bucket, self._sk(user_id, session_id, "calling_filling_logs.json"), data)

    # ── Utility ────────────────────────────────────────────────────────

    def list_user_sessions(self, user_id):
        prefix = f"{user_id}/sessions/"
        try:
            resp = self.s3.list_objects_v2(Bucket=self.output_bucket, Prefix=prefix, Delimiter="/")
            return [
                p["Prefix"].replace(prefix, "").rstrip("/")
                for p in resp.get("CommonPrefixes", [])
            ]
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

    # ── Config loaders ─────────────────────────────────────────────────

    def load_config(self, filename: str) -> dict:
        data = self._get(self.config_bucket, filename)
        if data is None:
            raise FileNotFoundError(f"Config not found in S3: {self.config_bucket}/{filename}")
        return data

    def load_investor_type_config(self, filename: str) -> dict:
        key = f"global_investor_type_keys/{filename}"
        data = self._get(self.config_bucket, key)
        if data is None:
            return self.load_config("form_keys.json")
        return data
