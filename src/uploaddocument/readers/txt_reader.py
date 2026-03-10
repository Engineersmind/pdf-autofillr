"""Plain text reader."""
from __future__ import annotations
from uploaddocument.readers.base_reader import DocumentReader


class TxtReader(DocumentReader):
    def read(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
