"""
Example 3 — OpenAI Embeddings backend.
Higher quality embeddings via text-embedding-3-small/large.

Install:
    pip install ragpdf-sdk[openai]
"""
import os
from ragpdf import RAGPDFClient, LocalStorage, LocalVectorStore, OpenAIEmbeddingBackend, OpenAICorrectorBackend

client = RAGPDFClient(
    storage=LocalStorage("./ragpdf_data"),
    vector_store=LocalVectorStore("./ragpdf_data"),
    embedding_backend=OpenAIEmbeddingBackend(
        api_key=os.environ["OPENAI_API_KEY"],
        model="text-embedding-3-small",  # or text-embedding-3-large
    ),
    corrector=OpenAICorrectorBackend(
        api_key=os.environ["OPENAI_API_KEY"],
        model="gpt-4-turbo-preview",
    ),
)
print("Client ready with OpenAI backends")
