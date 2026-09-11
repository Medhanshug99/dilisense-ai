FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model + reranker during build
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-large-en-v1.5')" && \
    python -c "from sentence_transformers import CrossEncoder; \
    CrossEncoder('BAAI/bge-reranker-large')"

COPY . .

CMD ["python", "-m", "app.main"]
