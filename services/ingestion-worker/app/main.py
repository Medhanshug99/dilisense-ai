"""
FastAPI app for health checks + manual job triggering (optional).
Worker runs in the same process via asyncio background task.
"""
import asyncio
import logging
import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .worker import run_worker

log = logging.getLogger("ingestion-worker")

app = FastAPI(title="ingestion-worker", version="0.1.0")


class JobTriggerRequest(BaseModel):
    document_id: str
    storage_path: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/jobs/trigger")
async def trigger_job(body: JobTriggerRequest):
    """
    Manual trigger for testing / re-processing without going through api-gateway.
    Enqueues directly into Redis using bullmq-python's Queue class.
    """
    from bullmq import Queue
    queue = Queue(settings.queue_name, {"host": settings.redis_host, "port": settings.redis_port})
    job = await queue.add("ingest", {"document_id": body.document_id, "storage_path": body.storage_path})
    await queue.close()
    return {"job_id": job.id, "queue": settings.queue_name}


# Run BullMQ worker in a background thread (bullmq-python uses asyncio internally)
# FastAPI's lifespan handles startup/shutdown.
_worker_started = False


@app.on_event("startup")
def startup():
    global _worker_started
    if not _worker_started:
        t = threading.Thread(target=lambda: asyncio.run(_run()), daemon=True)
        t.start()
        _worker_started = True
        log.info("BullMQ worker thread started")


async def _run():
    worker = run_worker()
    # Keep worker alive — run_forever is blocking
    import time
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
