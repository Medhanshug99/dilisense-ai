-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Documents table
CREATE TABLE documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type TEXT    NOT NULL,  -- 'pdf', 'html', 'docx', 'url'
    source_uri  TEXT    NOT NULL,
    title       TEXT,
    metadata    JSONB   DEFAULT '{}',
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending, processing, done, failed
    error_msg   TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Chunks table (text chunks with optional sparse + dense embeddings)
CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID    NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    chunk_level     TEXT    NOT NULL DEFAULT 'child',  -- 'root' | 'parent' | 'child'
    parent_chunk_id UUID    REFERENCES chunks(id) ON DELETE SET NULL,
    page_number     INTEGER,
    bounding_box    JSONB,
    text            TEXT    NOT NULL,
    text_vector     TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    embedding       VECTOR(1024),  -- bge-large-en-v1.5
    metadata        JSONB   DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_document_id ON chunks(document_id);
CREATE INDEX idx_chunks_text_vector ON chunks USING GIN(text_vector);
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);

-- Job queue (Redis holds actual queue; this is job metadata)
CREATE TABLE jobs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id  UUID    REFERENCES documents(id) ON DELETE CASCADE,
    job_type     TEXT    NOT NULL,  -- 'ingest', 'embed', 'reindex'
    status       TEXT    NOT NULL DEFAULT 'queued',  -- queued, running, done, failed
    worker_id    TEXT,
    error_msg    TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_document_id ON jobs(document_id);

-- Vector similarity search (bge-large-en-v1.5, 1024-dim, cosine):
--   SELECT id, 1 - (embedding <=> $1::vector) AS similarity, text
--   FROM chunks
--   WHERE embedding IS NOT NULL
--   ORDER BY embedding <=> $1::vector
--   LIMIT $2;

-- Text search:
--   SELECT id, ts_rank(text_vector, plainto_tsquery('english', $1)) AS rank, text
--   FROM chunks
--   WHERE text_vector @@ plainto_tsquery('english', $1);
