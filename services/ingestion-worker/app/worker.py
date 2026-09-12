"""
BullMQ worker listening on 'document-ingestion'.
Picks up { document_id, storage_path } jobs from the queue populated by
the Node api-gateway. Same Redis protocol — bullmq-python 2.24.0 and
bullmq-node 6.3.4 share the .lua scripts.
"""
import logging

from bullmq import Worker, Job

from .config import settings
from .layout_parser import extract_pages, sanity_check
from .chunker import BPEChunker
from .embedder import Embedder
from .persistence import insert_chunks, mark_document_status

log = logging.getLogger("ingestion-worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

chunker = BPEChunker()
embedder = Embedder()


async def process_job(job: Job) -> dict:
    """
    job.data is the dict the Node producer pushed: { document_id, storage_path }
    """
    data = job.data
    document_id = data.get("document_id")
    storage_path = data.get("storage_path")

    if not document_id or not storage_path:
        raise ValueError(f"job {job.id} missing document_id or storage_path: {data}")

    log.info(f"Processing job {job.id} for document {document_id} at {storage_path}")

    # Phase 1: status → processing
    await mark_document_status(document_id, "processing")

    # Phase 2: layout parsing
    pages = extract_pages(storage_path)
    log.info(f"Extracted {len(pages)} pages")

    # Phase 2b: sanity check — flag scanned/image-only PDFs before wasting compute
    check = sanity_check(pages)
    log.info(
        f"Text density: {check.chars_per_page:.1f} chars/page "
        f"({check.total_chars} total, {check.page_count} pages)"
    )
    if check.is_likely_scanned:
        log.warning(f"Document {document_id}: {check.reason}")
        await mark_document_status(
            document_id,
            "needs_review",
            f"likely_scanned: {check.reason}",
        )
        return {
            "document_id": document_id,
            "status": "needs_review",
            "reason": check.reason,
            "pages": len(pages),
        }

    # Phase 3: parent-child chunking
    children, parents = chunker.chunk_pages(pages)
    log.info(f"Generated {len(children)} children, {len(parents)} parents")

    if not children:
        await mark_document_status(
            document_id,
            "needs_review",
            "No text chunks extracted — document may be corrupted or empty.",
        )
        return {"document_id": document_id, "status": "needs_review", "reason": "no chunks"}

    # Phase 4: embed children only (parents are for context expansion at retrieval)
    child_texts = [c.text for c in children]
    vectors = embedder.embed(child_texts) if child_texts else []
    log.info(f"Embedded {len(vectors)} child vectors (dim={len(vectors[0]) if vectors else 0})")

    # Phase 5: persist to Postgres
    await insert_chunks(document_id, children, parents, vectors)

    # Phase 6: mark done
    await mark_document_status(document_id, "done")
    log.info(f"Document {document_id} marked done")

    return {
        "document_id": document_id,
        "status": "done",
        "pages": len(pages),
        "children": len(children),
        "parents": len(parents),
    }


def run_worker():
    worker = Worker(
        settings.queue_name,
        process_job,
        {
            "connection": {
                "host": settings.redis_host,
                "port": settings.redis_port,
            }
        },
    )
    worker.on("completed", lambda job, result: log.info(f"job {job.id} completed: {result}"))
    worker.on("failed", lambda job, err: log.error(f"job {job.id} failed: {err}"))
    log.info(f"Worker listening on queue '{settings.queue_name}'")
    return worker
