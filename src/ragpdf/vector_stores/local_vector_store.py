# src/ragpdf/vector_stores/local_vector_store.py
import json
import logging
import os
from datetime import datetime
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from ragpdf.vector_stores.base import VectorStoreBackend
from ragpdf.utils.helpers import generate_vector_id
from ragpdf.config.settings import (
    PREDICTION_THRESHOLD, TOP_K,
    CONFIDENCE_DECAY_RATE, CONFIDENCE_GROWTH_RATE,
    MAX_CONFIDENCE, MIN_CONFIDENCE,
)

logger = logging.getLogger(__name__)


class LocalVectorStore(VectorStoreBackend):
    """
    Flat-JSON vector store backed by the local filesystem.
    Perfect for development, testing, and small deployments.

    All vectors are loaded into memory on init, queries are fast
    (cosine similarity via numpy/sklearn).

    Usage:
        store = LocalVectorStore(path="./ragpdf_data")
    """

    def __init__(self, path: str = "./ragpdf_data"):
        self.path = path
        self.db_file = os.path.join(path, "vectors", "vector_database.json")
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        self.data = self._load()

    # ── Load ──────────────────────────────────────────────────────────────────
    def _load(self) -> dict:
        if not os.path.exists(self.db_file):
            logger.info("Vector DB not found — creating empty store.")
            return {"metadata": {"total_count": 0, "last_updated": _now()}, "vectors": []}
        with open(self.db_file, "r") as f:
            data = json.load(f)
        if "metadata" not in data:
            data["metadata"] = {"total_count": len(data.get("vectors", [])), "last_updated": _now()}
        self._backfill_missing_fields(data["vectors"])
        logger.info(f"Loaded {len(data['vectors'])} vectors from {self.db_file}")
        return data

    def _backfill_missing_fields(self, vectors: list):
        """Ensure all vectors have required tracking fields (handles old data)."""
        now = _now()
        for v in vectors:
            v.setdefault("confidence_history", [v.get("confidence", 0.75)])
            v.setdefault("positive_count", 0)
            v.setdefault("negative_count", 0)
            v.setdefault("usage_count", 0)
            v.setdefault("stability_score", 1.0)
            v.setdefault("avg_confidence", v["confidence_history"][-1])
            v.setdefault("error_history", [])
            v.setdefault("created_at", now)
            v.setdefault("last_updated", now)
            v.setdefault("last_used", now)

    # ── Save ──────────────────────────────────────────────────────────────────
    def save(self) -> None:
        self.data["metadata"]["last_updated"] = _now()
        self.data["metadata"]["total_count"] = len(self.data["vectors"])
        with open(self.db_file, "w") as f:
            json.dump(self.data, f, indent=2)

    # ── Find Similar ──────────────────────────────────────────────────────────
    def find_similar(self, query_embedding: list,
                     threshold: float = PREDICTION_THRESHOLD,
                     top_k: int = TOP_K) -> dict:
        vectors = self.data["vectors"]
        if not vectors:
            return {"matched": False, "confidence": 0.0, "top_k": [], "similarity_margin": 0.0}

        embeddings = np.array([v["embedding"] for v in vectors])
        sims = cosine_similarity([query_embedding], embeddings)[0]
        top_indices = np.argsort(sims)[-top_k:][::-1]

        top_k_results = [
            {"field_name": vectors[i]["field_name"],
             "confidence": float(sims[i]),
             "vector_id": vectors[i]["vector_id"]}
            for i in top_indices
        ]

        best_idx = top_indices[0]
        best_vec = vectors[best_idx]
        best_conf = float(sims[best_idx])
        margin = top_k_results[0]["confidence"] - top_k_results[1]["confidence"] if len(top_k_results) >= 2 else 0.0

        if best_conf >= threshold:
            best_vec["usage_count"] = best_vec.get("usage_count", 0) + 1
            best_vec["last_used"] = _now()
            return {
                "matched": True,
                "vector_id": best_vec["vector_id"],
                "field_name": best_vec["field_name"],
                "confidence": best_conf,
                "vector_confidence": best_vec.get("confidence_history", [0.75])[-1],
                "positive_count": best_vec.get("positive_count", 0),
                "negative_count": best_vec.get("negative_count", 0),
                "usage_count": best_vec.get("usage_count", 0),
                "stability_score": best_vec.get("stability_score", 1.0),
                "top_k": top_k_results,
                "similarity_margin": float(margin),
            }
        return {
            "matched": False,
            "confidence": best_conf,
            "best_candidate": best_vec["field_name"],
            "top_k": top_k_results,
            "similarity_margin": float(margin),
        }

    # ── Add Vector ────────────────────────────────────────────────────────────
    def add_vector(self, field_name: str, context: str, section_context: str,
                   headers: list, embedding: list, **metadata) -> str:
        vector_id = generate_vector_id(self.data["vectors"])
        now = _now()
        self.data["vectors"].append({
            "vector_id": vector_id,
            "field_name": field_name,
            "context": context,
            "section_context": section_context,
            "headers": headers,
            "embedding": embedding,
            "confidence_history": [0.75],
            "positive_count": 1,
            "negative_count": 0,
            "usage_count": 1,
            "stability_score": 1.0,
            "avg_confidence": 0.75,
            "error_history": [],
            "created_at": now,
            "last_updated": now,
            "last_used": now,
            **metadata,
        })
        logger.info(f"Added vector {vector_id}: {field_name}")
        return vector_id

    # ── Update Confidence ─────────────────────────────────────────────────────
    def update_confidence(self, vector_id: str, is_positive: bool,
                          error_info: Optional[dict] = None) -> Optional[float]:
        for vector in self.data["vectors"]:
            if vector["vector_id"] != vector_id:
                continue
            now = _now()
            hist = vector.setdefault("confidence_history", [0.75])
            current = hist[-1]

            if is_positive:
                new_conf = min(current * CONFIDENCE_GROWTH_RATE, MAX_CONFIDENCE)
                vector["positive_count"] = vector.get("positive_count", 0) + 1
            else:
                new_conf = max(current * CONFIDENCE_DECAY_RATE, MIN_CONFIDENCE)
                vector["negative_count"] = vector.get("negative_count", 0) + 1
                if error_info:
                    vector.setdefault("error_history", []).append({
                        "timestamp": now,
                        "pdf_hash": error_info.get("pdf_hash"),
                        "error_type": error_info.get("error_type"),
                        "user_feedback": error_info.get("user_feedback"),
                        "corrected_to": error_info.get("corrected_field_name"),
                        "original_confidence": current,
                    })
                    self._regenerate_embedding(vector, error_info)

            hist.append(round(new_conf, 6))
            total = vector.get("positive_count", 0) + vector.get("negative_count", 0)
            vector["stability_score"] = round(vector.get("positive_count", 0) / total, 4) if total else 1.0
            vector["avg_confidence"] = round(sum(hist) / len(hist), 6)
            vector["usage_count"] = vector.get("usage_count", 0) + 1
            vector["last_updated"] = now
            vector["last_used"] = now
            logger.info(f"Vector {vector_id}: {current:.4f} -> {new_conf:.4f} ({'pos' if is_positive else 'neg'})")
            return new_conf

        logger.warning(f"Vector {vector_id} not found")
        return None

    def _regenerate_embedding(self, vector: dict, error_info: dict):
        """Regenerate embedding enriched with the corrected field name."""
        try:
            from ragpdf.embeddings.factory import EmbeddingFactory
            gen = EmbeddingFactory.create()
            base = gen.create_text_from_field(vector)
            corrected = error_info.get("corrected_field_name", "")
            enriched = f"{base} corrected:{corrected}".strip() if corrected else base
            vector["embedding"] = gen.embed(enriched)
            logger.info(f"Regenerated embedding for {vector['vector_id']} -> {corrected}")
        except Exception as e:
            logger.warning(f"Embedding regen failed: {e}")

    def count(self) -> int:
        return len(self.data["vectors"])

    def find_by_name(self, field_name: str) -> Optional[str]:
        """Find vector_id by exact field_name match."""
        for v in self.data["vectors"]:
            if v.get("field_name") == field_name:
                return v["vector_id"]
        return None
