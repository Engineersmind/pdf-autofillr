"""Abstract DocumentReader."""
from __future__ import annotations
from abc import ABC, abstractmethod


class DocumentReader(ABC):
    @abstractmethod
    def read(self, file_path: str) -> str:
        """Extract all text from the document and return as a single string."""
