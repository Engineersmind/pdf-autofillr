"""
APILogger — comprehensive logger for all API calls and processing steps.
Ported from logger_utils.py in the original Lambda codebase.
"""
from __future__ import annotations
import json
import traceback
from datetime import datetime
from typing import Optional


class APILogger:
    """
    Tracks API requests, responses, processing steps, and errors.
    Can save full logs to S3 as execution_logs.json.
    """

    def __init__(self):
        self.logs = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "api_calls": [],
            "process_logs": [],
            "errors": [],
        }

    def log_api_request(self, operation: str, url: str, headers: dict, payload: dict):
        print(f"\n{chr(45)*60}\n📤 API REQUEST: {operation} | {url}")
        self.logs["api_calls"].append({
            "type": "request", "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation": operation, "url": url, "headers": headers, "payload": payload,
        })

    def log_api_response(self, operation: str, status_code: int, response_data: dict, duration_seconds: float):
        print(f"📥 API RESPONSE: {operation} | {status_code} | {duration_seconds}s")
        self.logs["api_calls"].append({
            "type": "response", "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation": operation, "status_code": status_code,
            "response_data": response_data, "duration_seconds": duration_seconds,
        })

    def log_process(self, message: str):
        print(message)
        self.logs["process_logs"].append({"timestamp": datetime.utcnow().isoformat() + "Z", "message": message})

    def log_error(self, message: str, details: Optional[dict] = None, exception: Optional[Exception] = None):
        entry = {"timestamp": datetime.utcnow().isoformat() + "Z", "message": message}
        if details:
            entry["details"] = details
        if exception:
            entry["exception_type"] = type(exception).__name__
            entry["exception_message"] = str(exception)
            entry["traceback"] = traceback.format_exc()
        print(f"\n{chr(33)*60}\n❌ ERROR: {message}\n{chr(33)*60}")
        self.logs["errors"].append(entry)

    def get_summary(self) -> dict:
        return {
            **self.logs,
            "summary": {
                "total_api_calls": len([x for x in self.logs["api_calls"] if x["type"] == "request"]),
                "total_process_logs": len(self.logs["process_logs"]),
                "total_errors": len(self.logs["errors"]),
                "success": len(self.logs["errors"]) == 0,
            },
        }

    def print_summary(self):
        s = self.get_summary()["summary"]
        print(f"\n{chr(61)*60}")
        print(f"📊 SUMMARY | API calls: {s['total_api_calls']} | Errors: {s['total_errors']} | Success: {s['success']}")
        print(f"{chr(61)*60}\n")

    def save_logs_to_s3(self, s3_uri: str) -> bool:
        """Save full execution logs as JSON to S3."""
        try:
            import boto3
            bucket, key = s3_uri.replace("s3://", "").split("/", 1)
            log_data = self.get_summary()
            log_data["end_timestamp"] = datetime.utcnow().isoformat() + "Z"
            boto3.client("s3").put_object(
                Bucket=bucket, Key=key,
                Body=json.dumps(log_data, indent=2, default=str),
                ContentType="application/json",
            )
            print(f"✅ Logs saved to S3: {s3_uri}")
            return True
        except Exception as e:
            print(f"⚠️ Failed to save logs to S3: {e}")
            return False
