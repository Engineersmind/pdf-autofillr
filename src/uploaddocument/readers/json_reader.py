"""JSON reader."""
from __future__ import annotations
import json
from uploaddocument.readers.base_reader import DocumentReader


class JsonReader(DocumentReader):
    def read(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.dumps(json.load(f), indent=2)
