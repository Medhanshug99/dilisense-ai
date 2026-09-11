"""
Embeds text chunks using BAAI/bge-large-en-v1.5 via sentence-transformers.
Model: 1024-dim, normalized vectors. cosine similarity via dot product (after normalization).
"""
from sentence_transformers import SentenceTransformer
from .config import settings


class Embedder:
    def __init__(self):
        # Lazy: load on first use, not at import time (GPU memory in container)
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(settings.embedding_model)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Returns normalized 1024-dim float vectors for the given texts.
        bge-large-en-v1.5 produces normalized outputs by default.
        """
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()
