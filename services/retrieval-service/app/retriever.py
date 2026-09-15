"""
Hybrid retrieval: dense (vector) + sparse (BM25) → RRF → rerank → parent expansion.

Pipeline:
  1. Dense: embed query → pgvector cosine → top-50 child chunks
  2. Sparse: ts_rank_cd against chunks.text_vector → top-50 child chunks
  3. RRF: Reciprocal Rank Fusion (k=60) across the two ranked lists → fused top-20
  4. Rerank: bge-reranker-large CrossEncoder on fused top-20 → final top-5
  5. Parent expansion: fetch parent.text for each final child via parent_chunk_id
"""
import asyncio
import logging
import psycopg.rows
from .config import settings
from .db import get_conn
from .embedder import Embedder
from .reranker import Reranker

log = logging.getLogger("retrieval")

# Ponytail: SQL is hand-written, no f-string substitution. Use psycopg %s placeholders only.
DENSE_SQL = """
    SELECT id, document_id, chunk_index, chunk_level, page_number,
           bounding_box, text, parent_chunk_id,
           1 - (embedding <=> %s::vector) AS similarity
    FROM chunks
    WHERE chunk_level = 'child'
    {doc_filter}
    ORDER BY embedding <=> %s::vector
    LIMIT %s
"""

SPARSE_SELECT = """
    SELECT id, document_id, chunk_index, chunk_level, page_number,
           bounding_box, text, parent_chunk_id,
           ts_rank_cd(text_vector, plainto_tsquery('english', %s)) AS rank
    FROM chunks
    WHERE chunk_level = 'child'
      AND text_vector @@ plainto_tsquery('english', %s)
    {doc_filter}
    ORDER BY ts_rank_cd(text_vector, plainto_tsquery('english', %s)) DESC
    LIMIT %s
"""


class Retriever:
    def __init__(self):
        self.embedder = Embedder()
        self.reranker = Reranker()

    async def search(self, query: str, document_id: str | None = None, top_k: int | None = None):
        top_k = top_k or settings.final_top_k

        query_vec = self.embedder.embed([query])[0]

        dense_rows, sparse_rows = await asyncio.gather(
            self._dense_search(query_vec, document_id),
            self._sparse_search(query, document_id),
        )
        log.info(f"Dense hits: {len(dense_rows)}, Sparse hits: {len(sparse_rows)}")

        fused = self._rrf_fusion(dense_rows, sparse_rows, top_n=settings.fused_top_n)
        log.info(f"RRF fused: {len(fused)} chunks")

        reranked = self.reranker.rerank(query, fused)
        final = reranked[:top_k]

        await self._expand_parents(final)
        return final

    async def _dense_search(self, query_vec: list[float], document_id: str | None):
        doc_filter = "AND document_id = %s" if document_id else ""
        sql = DENSE_SQL.format(doc_filter=doc_filter)
        if document_id:
            params = (query_vec, document_id, query_vec, settings.dense_top_n)
        else:
            params = (query_vec, query_vec, settings.dense_top_n)
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def _sparse_search(self, query: str, document_id: str | None):
        doc_filter = "AND document_id = %s" if document_id else ""
        sql = SPARSE_SELECT.format(doc_filter=doc_filter)
        if document_id:
            params = (query, query, document_id, query, settings.sparse_top_n)
        else:
            params = (query, query, query, settings.sparse_top_n)
        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(sql, params)
                rows = await cur.fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _rrf_fusion(dense_rows: list[dict], sparse_rows: list[dict], rrf_k: int = 60, top_n: int = 20) -> list[dict]:
        """
        Reciprocal Rank Fusion in plain Python.
        k=60 (standard constant that dampens rank differences).
        Returns top_n chunks sorted by fused RRF score (desc).
        """
        rrf_scores: dict[str, float] = {}
        dense_ranks: dict[str, int] = {}
        sparse_ranks: dict[str, int] = {}

        for rank, row in enumerate(dense_rows, start=1):
            chunk_id = str(row["id"])
            dense_ranks[chunk_id] = rank
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)

        for rank, row in enumerate(sparse_rows, start=1):
            chunk_id = str(row["id"])
            sparse_ranks[chunk_id] = rank
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (rrf_k + rank)

        fused_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_n]

        by_id: dict[str, dict] = {str(row["id"]): dict(row) for row in dense_rows + sparse_rows}

        result = []
        for chunk_id in fused_ids:
            row = by_id.get(chunk_id, {})
            row["dense_rank"] = dense_ranks.get(chunk_id)
            row["sparse_rank"] = sparse_ranks.get(chunk_id)
            row["rrf_score"] = rrf_scores[chunk_id]
            result.append(row)

        return result

    async def _expand_parents(self, chunks: list[dict]) -> None:
        """Fetch parent.text for each child chunk and attach."""
        parent_ids = list(set(str(c["parent_chunk_id"]) for c in chunks if c.get("parent_chunk_id")))
        if not parent_ids:
            for c in chunks:
                c["parent_text"] = None
            return

        async with get_conn() as conn:
            async with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                await cur.execute(
                    "SELECT id, text FROM chunks WHERE id = ANY(%s::uuid[])",
                    (parent_ids,),
                )
                rows = await cur.fetchall()
        parents_by_id = {str(r["id"]): r["text"] for r in rows}

        for c in chunks:
            pid = c.get("parent_chunk_id")
            c["parent_text"] = parents_by_id.get(str(pid)) if pid else None
