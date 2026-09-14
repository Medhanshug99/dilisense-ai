"""
Database write operations: update document status, insert chunks + embeddings.
Uses psycopg3 connection pool.
"""
import json
from typing import List
from .chunker import ChildChunk, ParentChunk
from .db import get_conn


async def mark_document_status(document_id: str, status: str, error_msg: str = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET status = %s, error_msg = %s, updated_at = NOW() WHERE id = %s",
            (status, error_msg, document_id),
        )


async def insert_chunks(
    document_id: str,
    children: List[ChildChunk],
    parents: List[ParentChunk],
    vectors: List[List[float]],
) -> None:
    """
    Insert parents first (children FK to them via parent_chunk_id),
    then children with embeddings.
    """
    # Idempotency defense: delete any pre-existing chunks for this document
    # so that even if the same job runs twice, stale data from the first run
    # is cleared and won't accumulate.
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM chunks WHERE document_id = %s",
            (document_id,),
        )
        # Parents
        for p in parents:
            conn.execute(
                """
                INSERT INTO chunks (id, document_id, chunk_index, chunk_level,
                                    page_number, bounding_box, text)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                """,
                (p.id, document_id, 0, "parent",
                 p.page_number, json.dumps(p.bbox), p.text),
            )

        # Children + embeddings
        for i, child in enumerate(children):
            vec = vectors[i] if i < len(vectors) else None
            vec_str = "[" + ",".join(str(x) for x in vec) + "]" if vec else None
            conn.execute(
                """
                INSERT INTO chunks (id, document_id, chunk_index, chunk_level,
                                    parent_chunk_id, page_number, bounding_box, text, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::vector)
                """,
                (
                    child.id, document_id, i, "child",
                    child.parent_id or None, child.page_number,
                    json.dumps(child.bbox), child.text, vec_str,
                ),
            )
