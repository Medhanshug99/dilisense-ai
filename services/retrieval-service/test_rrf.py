"""
RRF math test: pick a few real child chunks from the DB, query them, log the
fused ranks + scores. Doesn't require a full model — runs against the live DB.

Steps:
  1. Pick a random document + a keyword in its text.
  2. Run dense + sparse (no embedding needed if we use a known-good query).
  3. Show dense_ranks, sparse_ranks, RRF math, top-20 fused, then hand-traced math.
"""
import asyncio
import sys
import psycopg
from app.db import get_conn
from app.retriever import Retriever
from app.embedder import Embedder

# Pretty-print
def banner(s):
    print(f"\n{'='*60}\n{s}\n{'='*60}")


async def main():
    async with get_conn() as conn:
        doc_row = await conn.fetchrow(
            "SELECT id, title FROM documents WHERE status='done' LIMIT 1"
        )
    if not doc_row:
        print("No completed documents in DB. Run ingestion first.")
        sys.exit(0)
    document_id = doc_row["id"]
    print(f"Document: {document_id}  title={doc_row['title']!r}")

    # Pick a real chunk's text to use as our query
    async with get_conn() as conn:
        c = await conn.fetchrow(
            """
            SELECT text FROM chunks
            WHERE document_id = %s AND chunk_level = 'child'
            ORDER BY random() LIMIT 1
            """,
            document_id,
        )
    if not c:
        print("No child chunks.")
        sys.exit(0)

    query = c["text"][:200]  # truncate for cleaner output
    print(f"Query (taken from a real child chunk):\n  {query!r}\n")

    # Run RRF math explicitly
    embedder = Embedder()
    query_vec = embedder.embed([query])[0]
    retriever = Retriever()

    dense_rows = await retriever._dense_search(query_vec, str(document_id))
    sparse_rows = await retriever._sparse_search(query, str(document_id))

    banner("DENSE TOP-10 (vector cosine, bge-large-en-v1.5)")
    for r in dense_rows[:10]:
        print(f"  rank {dense_rows.index(r)+1:2d}  sim={r['similarity']:.4f}  id={r['id']}  text={r['text'][:60]!r}")

    banner("SPARSE TOP-10 (ts_rank_cd, BM25-ish)")
    for r in sparse_rows[:10]:
        print(f"  rank {sparse_rows.index(r)+1:2d}  rank_score={r['rank']:.4f}  id={r['id']}  text={r['text'][:60]!r}")

    fused = retriever._rrf_fusion(dense_rows, sparse_rows, rrf_k=60, top_n=20)

    banner("RRF FUSION (k=60)")
    print("formula:  rrf_score = 1/(k+dense_rank) + 1/(k+sparse_rank)")
    print("  - chunk in only one list: only one term added")
    print("  - chunk in both lists: score = sum of two terms")
    print()
    for c in fused:
        d = c.get("dense_rank")
        s = c.get("sparse_rank")
        d_term = f"1/(60+{d})={1/(60+d):.6f}" if d else "       —"
        s_term = f"1/(60+{s})={1/(60+s):.6f}" if s else "       —"
        both = d and s
        marker = "BOTH" if both else ("DENSE" if d else "SPARSE")
        print(f"  {marker:5s}  rrf={c['rrf_score']:.6f}  "
              f"d={d if d else '—':>3}  s={s if s else '—':>3}  "
              f"{d_term} + {s_term}  text={c['text'][:50]!r}")

    banner("DONE")


if __name__ == "__main__":
    asyncio.run(main())
