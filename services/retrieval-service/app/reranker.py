"""CrossEncoder reranker using BAAI/bge-reranker-large."""
from sentence_transformers import CrossEncoder
from .config import settings


class Reranker:
    def __init__(self):
        self._model = None

    @property
    def model(self):
        if self._model is None:
            self._model = CrossEncoder(settings.reranker_model)
        return self._model

    def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """
        chunks: list of dicts with 'text' and other metadata.
        Returns chunks re-sorted by rerank score (desc), with 'rerank_score' added.
        """
        if not chunks:
            return []
        pairs = [(query, c["text"]) for c in chunks]
        scores = self.model.predict(pairs, show_progress_bar=False).tolist()
        for c, s in zip(chunks, scores):
            c["rerank_score"] = float(s)
        chunks.sort(key=lambda c: c["rerank_score"], reverse=True)
        return chunks
