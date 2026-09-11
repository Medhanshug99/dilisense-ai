"""Pydantic request/response models for the retrieval API."""
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    document_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResult(BaseModel):
    chunk_id: str
    child_text: str
    parent_text: str | None
    page_number: int | None
    bounding_box: dict | None
    dense_rank: int | None
    sparse_rank: int | None
    rrf_score: float
    rerank_score: float


class QueryResponse(BaseModel):
    query: str
    top_k: int
    results: list[QueryResult]
