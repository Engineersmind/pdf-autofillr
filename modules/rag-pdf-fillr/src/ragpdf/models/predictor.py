# src/ragpdf/models/predictor.py
import logging
from ragpdf.embeddings.base import EmbeddingBackend
from ragpdf.vector_stores.base import VectorStoreBackend
from ragpdf.config.settings import PREDICTION_THRESHOLD, TOP_K

logger = logging.getLogger(__name__)


class FieldPredictor:
    """
    Core RAG predictor.
    For each input field:
      1. Build text from field_name + context + section_context + headers
      2. Generate embedding via pluggable EmbeddingBackend
      3. Find best match via pluggable VectorStoreBackend (cosine similarity)
      4. Return prediction with confidence, top-k, and similarity margin
    """

    def __init__(self, embedding_backend: EmbeddingBackend, vector_store: VectorStoreBackend):
        self.embedding_backend = embedding_backend
        self.vector_store = vector_store

    def predict(self, fields: list) -> list:
        """
        Predict field names for a list of input fields.

        Each field should be a dict with:
            field_id        : str
            field_name      : str   (optional but improves accuracy)
            context         : str
            section_context : str
            headers         : list[str]

        Returns list of prediction dicts.
        """
        total = len(fields)
        logger.info(f"{'='*60}")
        logger.info(f"PREDICT: {total} fields | threshold={PREDICTION_THRESHOLD} | vectors={self.vector_store.count()}")
        logger.info(f"{'='*60}")

        if self.vector_store.count() == 0:
            logger.warning("Vector store is EMPTY — all predictions will be null. Seed vectors via /save-filled-pdf first.")

        predictions = []
        for i, field in enumerate(fields):
            text = self.embedding_backend.create_text_from_field(field)
            embedding = self.embedding_backend.embed(text)

            logger.info(f"[{i+1}/{total}] field_id={field['field_id']!r}")
            logger.info(f"         text : {text!r}")

            match = self.vector_store.find_similar(
                embedding, threshold=PREDICTION_THRESHOLD, top_k=TOP_K
            )

            if match.get("matched"):
                logger.info(f"         ✅ MATCH  → {match['field_name']!r}  confidence={match['confidence']:.4f}")
            else:
                best = match.get("best_candidate", "n/a")
                conf = match.get("confidence", 0.0)
                logger.info(f"         ❌ NO MATCH  best_candidate={best!r}  score={conf:.4f}  (need >={PREDICTION_THRESHOLD})")

            prediction = {
                "field_id": field["field_id"],
                "context": field.get("context", ""),
                "section_context": field.get("section_context", ""),
                "headers": field.get("headers", []),
                "_embedding": embedding,
                **match,
            }
            predictions.append(prediction)

        matched = sum(1 for p in predictions if p.get("matched"))
        logger.info(f"{'='*60}")
        logger.info(f"PREDICT DONE: {matched}/{total} matched")
        logger.info(f"{'='*60}")

        self.vector_store.save()
        return predictions
