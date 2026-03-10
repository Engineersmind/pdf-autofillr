# src/ragpdf/vector_stores/factory.py
from ragpdf.vector_stores.base import VectorStoreBackend


class VectorStoreFactory:
    @staticmethod
    def create() -> VectorStoreBackend:
        from ragpdf.config.settings import RAGPDF_VECTOR_STORE, RAGPDF_DATA_PATH
        vs = RAGPDF_VECTOR_STORE
        if vs == "s3":
            from ragpdf.vector_stores.s3_vector_store import S3VectorStore
            from ragpdf.config.settings import RAGPDF_S3_BUCKET, RAGPDF_S3_REGION, RAGPDF_S3_PREFIX
            return S3VectorStore(bucket=RAGPDF_S3_BUCKET, region=RAGPDF_S3_REGION, prefix=RAGPDF_S3_PREFIX)
        if vs == "pinecone":
            from ragpdf.vector_stores.pinecone_store import PineconeStore
            return PineconeStore()
        if vs == "chroma":
            from ragpdf.vector_stores.chroma_store import ChromaStore
            return ChromaStore()
        if vs == "weaviate":
            from ragpdf.vector_stores.weaviate_store import WeaviateStore
            return WeaviateStore()
        from ragpdf.vector_stores.local_vector_store import LocalVectorStore
        return LocalVectorStore(path=RAGPDF_DATA_PATH)
