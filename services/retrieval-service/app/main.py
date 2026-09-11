"""FastAPI app for hybrid retrieval."""
import logging
from fastapi import FastAPI
from .retriever import Retriever
from .schemas import QueryRequest, QueryResponse, QueryResult

log = logging.getLogger("retrieval-service")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

app = FastAPI(title="retrieval-service", version="0.1.0")
retriever = Retriever()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query/hybrid", response_model=QueryResponse)
async def query_hybrid(body: QueryRequest):
    chunks = await retriever.search(body.query, body.document_id, body.top_k)
    results = [
        QueryResult(
            chunk_id=str(c["id"]),
            child_text=c["text"],
            parent_text=c.get("parent_text"),
            page_number=c.get("page_number"),
            bounding_box=c.get("bounding_box"),
            dense_rank=c.get("dense_rank"),
            sparse_rank=c.get("sparse_rank"),
            rrf_score=c["rrf_score"],
            rerank_score=c["rerank_score"],
        )
        for c in chunks
    ]
    return QueryResponse(query=body.query, top_k=body.top_k, results=results)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001)
