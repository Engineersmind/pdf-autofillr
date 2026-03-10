"""ReaderFactory — picks the right reader by file extension."""
from __future__ import annotations
import os


class ReaderFactory:
    @classmethod
    def read(cls, file_path: str) -> str:
        """Pick reader by extension and return extracted text."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document not found: {file_path}")
        ext = os.path.splitext(file_path)[1].lower()
        readers = cls._registry()
        if ext not in readers:
            raise ValueError(f"Unsupported format: {ext!r}. Supported: {list(readers)}")
        return readers[ext]().read(file_path)

    @staticmethod
    def _registry() -> dict:
        from uploaddocument.readers.pdf_reader import PDFReader
        from uploaddocument.readers.docx_reader import DocxReader
        from uploaddocument.readers.pptx_reader import PptxReader
        from uploaddocument.readers.xlsx_reader import XlsxReader
        from uploaddocument.readers.json_reader import JsonReader
        from uploaddocument.readers.txt_reader import TxtReader
        return {
            ".pdf": PDFReader, ".docx": DocxReader, ".pptx": PptxReader,
            ".xlsx": XlsxReader, ".xls": XlsxReader,
            ".json": JsonReader, ".txt": TxtReader,
        }
