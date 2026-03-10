# src/ragpdf/config/settings.py
import os
from dotenv import load_dotenv

load_dotenv()

RAGPDF_STORAGE        = os.getenv("RAGPDF_STORAGE", "local")
RAGPDF_DATA_PATH      = os.getenv("RAGPDF_DATA_PATH", "./ragpdf_data")
RAGPDF_S3_BUCKET      = os.getenv("RAGPDF_S3_BUCKET", "")
RAGPDF_S3_REGION      = os.getenv("RAGPDF_S3_REGION", "us-east-1")
RAGPDF_S3_PREFIX      = os.getenv("RAGPDF_S3_PREFIX", "ragpdf/")

RAGPDF_EMBEDDING_BACKEND      = os.getenv("RAGPDF_EMBEDDING_BACKEND", "sentence_transformer")
RAGPDF_ST_MODEL               = os.getenv("RAGPDF_ST_MODEL", "all-MiniLM-L6-v2")
OPENAI_API_KEY                = os.getenv("OPENAI_API_KEY", "")
RAGPDF_OPENAI_EMBEDDING_MODEL = os.getenv("RAGPDF_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

RAGPDF_VECTOR_STORE       = os.getenv("RAGPDF_VECTOR_STORE", "local")
PINECONE_API_KEY          = os.getenv("PINECONE_API_KEY", "")
RAGPDF_PINECONE_INDEX     = os.getenv("RAGPDF_PINECONE_INDEX", "ragpdf-vectors")
RAGPDF_PINECONE_NAMESPACE = os.getenv("RAGPDF_PINECONE_NAMESPACE", "default")
RAGPDF_CHROMA_PATH        = os.getenv("RAGPDF_CHROMA_PATH", "./chroma_data")
RAGPDF_CHROMA_COLLECTION  = os.getenv("RAGPDF_CHROMA_COLLECTION", "ragpdf_vectors")
RAGPDF_WEAVIATE_URL       = os.getenv("RAGPDF_WEAVIATE_URL", "http://localhost:8080")
RAGPDF_WEAVIATE_API_KEY   = os.getenv("RAGPDF_WEAVIATE_API_KEY", "")
RAGPDF_WEAVIATE_CLASS     = os.getenv("RAGPDF_WEAVIATE_CLASS", "RagpdfVector")

RAGPDF_CORRECTOR_BACKEND  = os.getenv("RAGPDF_CORRECTOR_BACKEND", "openai")
RAGPDF_OPENAI_MODEL       = os.getenv("RAGPDF_OPENAI_MODEL", "gpt-4-turbo-preview")
RAGPDF_OPENAI_TEMPERATURE = float(os.getenv("RAGPDF_OPENAI_TEMPERATURE", "0.3"))
RAGPDF_OPENAI_MAX_TOKENS  = int(os.getenv("RAGPDF_OPENAI_MAX_TOKENS", "500"))
ANTHROPIC_API_KEY         = os.getenv("ANTHROPIC_API_KEY", "")
RAGPDF_ANTHROPIC_MODEL    = os.getenv("RAGPDF_ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

PREDICTION_THRESHOLD   = float(os.getenv("RAGPDF_PREDICTION_THRESHOLD", "0.75"))
TOP_K                  = int(os.getenv("RAGPDF_TOP_K", "5"))
AMBIGUITY_THRESHOLD    = float(os.getenv("RAGPDF_AMBIGUITY_THRESHOLD", "0.10"))
CONFIDENCE_DECAY_RATE  = float(os.getenv("RAGPDF_CONFIDENCE_DECAY_RATE", "0.95"))
CONFIDENCE_GROWTH_RATE = float(os.getenv("RAGPDF_CONFIDENCE_GROWTH_RATE", "1.05"))
MAX_CONFIDENCE         = float(os.getenv("RAGPDF_MAX_CONFIDENCE", "0.99"))
MIN_CONFIDENCE         = float(os.getenv("RAGPDF_MIN_CONFIDENCE", "0.50"))

RAGPDF_DEBUG     = os.getenv("RAGPDF_DEBUG", "false").lower() == "true"
RAGPDF_LOG_LEVEL = os.getenv("RAGPDF_LOG_LEVEL", "INFO")
