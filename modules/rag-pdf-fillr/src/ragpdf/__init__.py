# src/ragpdf/__init__.py
"""
ragpdf-sdk — Self-learning RAG field prediction for PDF form filling.

Quick start:
    from ragpdf import RAGPDFClient
    client = RAGPDFClient.from_env()

Full plugin setup:
    from ragpdf import (
        RAGPDFClient,
        LocalStorage, S3Storage,
        LocalVectorStore, S3VectorStore,
        SentenceTransformerBackend, OpenAIEmbeddingBackend,
        OpenAICorrectorBackend, AnthropicCorrectorBackend, NoOpCorrectorBackend,
    )
"""
from ragpdf.client import RAGPDFClient

# Storage backends
from ragpdf.storage.local_storage import LocalStorage
from ragpdf.storage.s3_storage import S3Storage

# Embedding backends
from ragpdf.embeddings.sentence_transformer import SentenceTransformerBackend
from ragpdf.embeddings.openai_embeddings import OpenAIEmbeddingBackend
from ragpdf.embeddings.noop_embeddings import NoOpEmbeddingBackend

# Vector store backends
from ragpdf.vector_stores.local_vector_store import LocalVectorStore
from ragpdf.vector_stores.s3_vector_store import S3VectorStore

# Corrector backends
from ragpdf.correctors.openai_corrector import OpenAICorrectorBackend
from ragpdf.correctors.anthropic_corrector import AnthropicCorrectorBackend
from ragpdf.correctors.noop_corrector import NoOpCorrectorBackend

__version__ = "0.1.1"
__all__ = [
    "RAGPDFClient",
    "LocalStorage", "S3Storage",
    "SentenceTransformerBackend", "OpenAIEmbeddingBackend", "NoOpEmbeddingBackend",
    "LocalVectorStore", "S3VectorStore",
    "OpenAICorrectorBackend", "AnthropicCorrectorBackend", "NoOpCorrectorBackend",
]
