"""
Embedding Service — Singleton wrapper around sentence-transformers.

Lazy-loads the model on first call to avoid startup delay.
Uses batch encoding for performance.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from marginalia.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Singleton embedding service using sentence-transformers."""

    _instance: "EmbeddingService | None" = None
    _model: Any = None  # SentenceTransformer once loaded

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading embedding model: {settings.embedding_model}")
            self._model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded.")
        return self._model

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """
        Encode a list of texts into normalized embeddings.

        Returns numpy array of shape (len(texts), embedding_dim).
        """
        if not texts:
            return np.array([])

        # Filter out empty strings
        clean_texts = [t if t and t.strip() else " " for t in texts]

        model = self._load_model()
        return model.encode(
            clean_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

    def encode_one(self, text: str) -> np.ndarray:
        """Encode a single text. Returns 1D vector."""
        result = self.encode([text])
        return result[0] if len(result) > 0 else np.zeros(384)

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two normalized embeddings."""
        if a.size == 0 or b.size == 0:
            return 0.0
        return float(np.dot(a, b))

    @staticmethod
    def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Compute pairwise cosine similarity matrix between two sets of embeddings."""
        if a.size == 0 or b.size == 0:
            return np.array([])
        return np.dot(a, b.T)


# Module-level singleton
embedder = EmbeddingService()
