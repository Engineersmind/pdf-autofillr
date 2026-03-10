# src/ragpdf/embeddings/factory.py
from ragpdf.embeddings.base import EmbeddingBackend


class EmbeddingFactory:
    @staticmethod
    def create() -> EmbeddingBackend:
        from ragpdf.config.settings import (
            RAGPDF_EMBEDDING_BACKEND, RAGPDF_ST_MODEL,
            OPENAI_API_KEY, RAGPDF_OPENAI_EMBEDDING_MODEL,
        )
        if RAGPDF_EMBEDDING_BACKEND == "openai":
            from ragpdf.embeddings.openai_embeddings import OpenAIEmbeddingBackend
            return OpenAIEmbeddingBackend(
                api_key=OPENAI_API_KEY, model=RAGPDF_OPENAI_EMBEDDING_MODEL
            )
        from ragpdf.embeddings.sentence_transformer import SentenceTransformerBackend
        return SentenceTransformerBackend(model=RAGPDF_ST_MODEL)
