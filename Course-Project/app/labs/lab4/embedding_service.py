"""Lazy local sentence embedding service for Lab 4 retrieval."""

import logging
import json
import threading
from pathlib import Path
from typing import Any, Sequence

import numpy as np

from config import settings

logger = logging.getLogger(__name__)

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EMBEDDING_DIMENSION = 384


class EmbeddingUnavailableError(RuntimeError):
    """Raised when the configured local embedding model cannot be used."""


class LocalEmbeddingService:
    """Load one pinned Sentence Transformer from disk and perform CPU-only inference."""

    model_id = MODEL_ID
    model_revision = MODEL_REVISION
    dimension = EMBEDDING_DIMENSION

    def __init__(self, model_path: str | Path | None = None) -> None:
        self.model_path = Path(model_path or settings.lab4_embedding_model_path).resolve()
        self._model = None
        self._lock = threading.RLock()

    def status(self) -> dict[str, object]:
        """Return local model availability without loading the model or using the network."""
        try:
            self._validate_model_bundle()
            available = True
            setup_error = None
        except EmbeddingUnavailableError as exc:
            available = False
            setup_error = str(exc)
        return {
            "available": available,
            "loaded": self._model is not None,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "dimension": self.dimension,
            "device": "cpu",
            "model_path": str(self.model_path),
            "setup_error": setup_error,
        }

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Encode texts with normalized vectors using only the local model files."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("Embedding inputs must be non-empty text.")

        with self._lock:
            model = self._load_model()
            try:
                vectors = np.asarray(
                    model.encode(
                        list(texts),
                        convert_to_numpy=True,
                        normalize_embeddings=True,
                        show_progress_bar=False,
                        batch_size=min(32, len(texts)),
                    ),
                    dtype=np.float32,
                )
            except Exception as exc:
                logger.error("Local embedding inference failed: %s", type(exc).__name__)
                raise EmbeddingUnavailableError(
                    f"Local embedding inference failed ({type(exc).__name__})."
                ) from exc

        if vectors.shape != (len(texts), self.dimension):
            raise EmbeddingUnavailableError(
                f"Embedding model returned shape {vectors.shape}; expected "
                f"({len(texts)}, {self.dimension})."
            )
        if not np.isfinite(vectors).all():
            raise EmbeddingUnavailableError("Embedding model returned non-finite vector values.")
        return vectors

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        self._validate_model_bundle()

        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                str(self.model_path),
                device="cpu",
                local_files_only=True,
                trust_remote_code=False,
            )
            if model.get_sentence_embedding_dimension() != self.dimension:
                raise ValueError(
                    f"Expected {self.dimension} embedding dimensions, got "
                    f"{model.get_sentence_embedding_dimension()}."
                )
            self._model = model
            logger.info(
                "Loaded local Lab 4 embedding model %s revision %s on CPU.",
                self.model_id,
                self.model_revision,
            )
            return model
        except Exception as exc:
            logger.error("Could not load local embedding model: %s", type(exc).__name__)
            raise EmbeddingUnavailableError(
                f"Could not load local embedding model from {self.model_path} "
                f"({type(exc).__name__})."
            ) from exc

    def _validate_model_bundle(self) -> None:
        if not self.model_path.is_dir():
            raise EmbeddingUnavailableError(
                f"Local embedding model directory is missing: {self.model_path}"
            )
        manifest_path = self.model_path / "courseagentai_model.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EmbeddingUnavailableError(
                f"Local embedding model manifest is missing or invalid at {manifest_path}."
            ) from exc
        if (
            manifest.get("model_id") != self.model_id
            or manifest.get("revision") != self.model_revision
            or manifest.get("dimension") != self.dimension
        ):
            raise EmbeddingUnavailableError(
                f"Local model manifest does not match the pinned model {self.model_id} "
                f"revision {self.model_revision}."
            )
        required_files = ("model.safetensors", "modules.json", "tokenizer.json")
        if any(not (self.model_path / filename).is_file() for filename in required_files):
            raise EmbeddingUnavailableError(
                f"Local embedding model files are incomplete in {self.model_path}."
            )


local_embedding_service = LocalEmbeddingService()
