"""PDF reader using PyMuPDF (fitz)."""
from __future__ import annotations
from uploaddocument.readers.base_reader import DocumentReader


class PDFReader(DocumentReader):
    def read(self, file_path: str) -> str:
        import fitz
        doc = fitz.open(file_path)
        pages = [page.get_text("text").strip() for page in doc if page.get_text("text").strip()]
        doc.close()
        return "\n\n".join(pages)
